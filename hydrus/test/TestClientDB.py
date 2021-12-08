import os
import time
import unittest

from mock import patch

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSerialisable
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientExporting
from hydrus.client import ClientSearch
from hydrus.client import ClientServices
from hydrus.client.db import ClientDB
from hydrus.client.gui.pages import ClientGUIManagement
from hydrus.client.gui.pages import ClientGUIPages
from hydrus.client.gui.pages import ClientGUISession
from hydrus.client.importing import ClientImportLocal
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileImportOptions
from hydrus.client.metadata import ClientTags

from hydrus.test import TestController

class TestClientDB( unittest.TestCase ):
    
    @classmethod
    def _clear_db( cls ):
        
        cls._delete_db()
        
        # class variable
        cls._db = ClientDB.DB( HG.test_controller, TestController.DB_DIR, 'client' )
        
        HG.test_controller.SetTestDB( cls._db )
        
    
    @classmethod
    def _delete_db( cls ):
        
        cls._db.Shutdown()
        
        while not cls._db.LoopIsFinished():
            
            time.sleep( 0.1 )
            
        
        db_filenames = list(cls._db._db_filenames.values())
        
        for filename in db_filenames:
            
            path = os.path.join( TestController.DB_DIR, filename )
            
            os.remove( path )
            
        
        del cls._db
        
        HG.test_controller.ClearTestDB()
        
    
    @classmethod
    def setUpClass( cls ):
        
        cls._db = ClientDB.DB( HG.test_controller, TestController.DB_DIR, 'client' )
        
        HG.test_controller.SetTestDB( cls._db )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._delete_db()
        
    
    def _read( self, action, *args, **kwargs ): return TestClientDB._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestClientDB._db.Write( action, True, *args, **kwargs )
    
    def test_autocomplete( self ):
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        tag_search_context = ClientSearch.TagSearchContext( service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY )
        
        TestClientDB._clear_db()
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'c*' )
        
        self.assertEqual( result, [] )
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'series:*' )
        
        self.assertEqual( result, [] )
        
        #
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        service_keys_to_content_updates = {}
        
        content_updates = []

        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
        service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = content_updates
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        # cars
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'c*', add_namespaceless = True )
        
        preds = set()
        
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'car', min_current_count = 1 ) )
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        # cars
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'c*', add_namespaceless = False )
        
        preds = set()
        
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 ) )
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'car', min_current_count = 1 ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'ser*' )
        
        self.assertEqual( result, [] )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'series:c*' )
        
        pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 )
        
        ( read_pred, ) = result
        
        self.assertEqual( read_pred.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'car', exact_match = True )
        
        pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'car', min_current_count = 1 )
        
        ( read_pred, ) = result
        
        self.assertEqual( read_pred.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'c', exact_match = True )
        
        self.assertEqual( result, [] )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = '*' )
        
        preds = set()
        
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'car', min_current_count = 1 ) )
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 ) )
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'maker:ford', min_current_count = 1 ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'series:*' )
        
        preds = set()
        
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'c*r*' )
        
        preds = set()
        
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'car', min_current_count = 1 ) )
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, CC.COMBINED_FILE_SERVICE_KEY, search_text = 'ser*', search_namespaces_into_full_tags = True )
        
        preds = set()
        
        preds.add( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
    
    def test_export_folders( self ):
        
        tag_search_context = ClientSearch.TagSearchContext( service_key = HydrusData.GenerateKey() )
        
        location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ HydrusData.GenerateKey() ] )
        
        file_search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context, tag_search_context = tag_search_context, predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'test' ) ] )
        
        export_folder = ClientExporting.ExportFolder( 'test path', export_type = HC.EXPORT_FOLDER_TYPE_REGULAR, delete_from_client_after_export = False, file_search_context = file_search_context, period = 3600, phrase = '{hash}' )
        
        self._write( 'serialisable', export_folder )
        
        [ result ] = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
        
        self.assertEqual( result.GetName(), export_folder.GetName() )
        
    
    def test_file_query_ids( self ):
        
        TestClientDB._clear_db()
        
        def run_namespace_predicate_tests( tests ):
            
            for ( inclusive, namespace, result ) in tests:
                
                predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, namespace, inclusive ) ]
                
                location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
                
                search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                for file_query_id in file_query_ids:
                    
                    self.assertEqual( type( file_query_id ), int )
                    
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_system_predicate_tests( tests ):
            
            for ( predicate_type, info, result ) in tests:
                
                predicates = [ ClientSearch.Predicate( predicate_type, info ) ]
                
                location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
                
                search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                for file_query_id in file_query_ids:
                    
                    self.assertEqual( type( file_query_id ), int )
                    
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_tag_predicate_tests( tests ):
            
            for ( inclusive, tag, result ) in tests:
                
                predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, tag, inclusive ) ]
                
                location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
                
                search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                for file_query_id in file_query_ids:
                    
                    self.assertEqual( type( file_query_id ), int )
                    
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_or_predicate_tests( tests ):
            
            for ( predicates, result ) in tests:
                
                location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
                
                search_context = ClientSearch.FileSearchContext( location_search_context = location_search_context, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                for file_query_id in file_query_ids:
                    
                    self.assertEqual( type( file_query_id ), int )
                    
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        tests = []
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_LOCAL, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        file_import_status = self._write( 'import_file', file_import_job )
        
        written_status = file_import_status.status
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_SUCCESSFUL_AND_NEW )
        self.assertEqual( written_note, '' )
        self.assertEqual( file_import_job.GetHash(), hash )
        
        time.sleep( 1.1 ) # to get timestamps right
        
        #
        
        tests = []
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 1, 1, 1, 1, ) ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 0, 0, ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( CC.UNICODE_ALMOST_EQUAL_TO, 'delta', ( 1, 1, 1, 1, ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( CC.UNICODE_ALMOST_EQUAL_TO, 'delta', ( 0, 0, 0, 0, ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 'delta', ( 1, 1, 1, 1, ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 'delta', ( 0, 0, 0, 0, ) ), 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '<', 100, ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '<', 0, ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( CC.UNICODE_ALMOST_EQUAL_TO, 100, ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( CC.UNICODE_ALMOST_EQUAL_TO, 0, ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '=', 100, ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '=', 0, ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '>', 100, ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '>', 0, ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True, 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False, 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, True, 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, False, 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, ( ( hash, ), 'sha256' ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, ( ( bytes.fromhex( '0123456789abcdef' * 4 ), ), 'sha256' ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 201 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 200 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( CC.UNICODE_ALMOST_EQUAL_TO, 200 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( CC.UNICODE_ALMOST_EQUAL_TO, 60 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( CC.UNICODE_ALMOST_EQUAL_TO, 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '=', 200 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '=', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '>', 200 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '>', 199 ), 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX, None, 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_LOCAL, None, 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, HC.IMAGES, 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, ( HC.IMAGE_PNG, ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, ( HC.IMAGE_JPEG, ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, HC.VIDEO, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 0 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 1 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '=', 0 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '=', 1 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '>', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '=', 0 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '=', 1 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '>', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '<', 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( CC.UNICODE_ALMOST_EQUAL_TO, 0 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( CC.UNICODE_ALMOST_EQUAL_TO, 1 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '=', 0 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '=', 1 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '>', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 1, 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 4, 3 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( CC.UNICODE_ALMOST_EQUAL_TO, 1, 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( CC.UNICODE_ALMOST_EQUAL_TO, 200, 201 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( CC.UNICODE_ALMOST_EQUAL_TO, 4, 1 ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( ( hash, ), 5 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( ( bytes.fromhex( '0123456789abcdef' * 4 ), ), 5 ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 0, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 5270, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 5271, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '=', 5270, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '=', 0, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( CC.UNICODE_ALMOST_EQUAL_TO, 5270, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( CC.UNICODE_ALMOST_EQUAL_TO, 0, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5270, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5269, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusData.ConvertUnitToInt( 'KB' ) ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusData.ConvertUnitToInt( 'MB' ) ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusData.ConvertUnitToInt( 'GB' ) ), 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '<', 201 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '<', 200 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( CC.UNICODE_ALMOST_EQUAL_TO, 200 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( CC.UNICODE_ALMOST_EQUAL_TO, 60 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( CC.UNICODE_ALMOST_EQUAL_TO, 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 200 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '>', 200 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '>', 199 ), 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 100, 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 1, 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 0, 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        service_keys_to_content_updates = {}
        
        service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( hash, ) ), )
        service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ), )
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        time.sleep( 0.5 )
        
        #
        
        tests = []
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 1 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 2 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 1 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 0 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 2 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '=', 0 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '=', 1 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '>', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 2 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 1 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '=', 0 ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '=', 1 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '>', 0 ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '>', 1 ), 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        tests = []
        
        tests.append( ( True, 'car', 1 ) )
        tests.append( ( False, 'car', 0 ) )
        tests.append( ( True, 'bus', 0 ) )
        tests.append( ( False, 'bus', 1 ) )
        
        run_tag_predicate_tests( tests )
        
        #
        
        tests = []
        
        tests.append( ( True, 'series', 0 ) )
        tests.append( ( False, 'series', 1 ) )
        
        run_namespace_predicate_tests( tests )
        
        #
        
        service_keys_to_content_updates = {}
        
        content_updates = []
        
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
        service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = content_updates
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( True, 'maker:ford', 1 ) )
        tests.append( ( True, 'ford', 1 ) )
        tests.append( ( False, 'maker:ford', 0 ) )
        tests.append( ( False, 'ford', 0 ) )
        
        run_tag_predicate_tests( tests )
        
        #
        
        tests = []
        
        tests.append( ( True, 'series', 1 ) )
        tests.append( ( False, 'series', 0 ) )
        
        run_namespace_predicate_tests( tests )
        
        #
        
        tests = []
        
        preds = []
        
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 201 ) ) )
        
        or_pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'truck' ) )
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 0 ) )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'truck', inclusive = False ) )
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'truck' ) )
        
        or_pred_1 = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'maker:toyota' ) )
        preds.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'maker:ford' ) )
        
        or_pred_2 = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred_1, or_pred_2 ], 1 ) )
        
        run_or_predicate_tests( tests )
        
        #
        
        from hydrus.test import TestController
        
        services = self._read( 'services' )
        
        services.append( ClientServices.GenerateService( TestController.LOCAL_RATING_LIKE_SERVICE_KEY, HC.LOCAL_RATING_LIKE, 'test like rating service' ) )
        services.append( ClientServices.GenerateService( TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.LOCAL_RATING_NUMERICAL, 'test numerical rating service' ) )
        
        self._write( 'update_services', services )
        
        service_keys_to_content_updates = {}
        
        content_updates = []
        
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, ( hash, ) ) ) )
        
        service_keys_to_content_updates[ TestController.LOCAL_RATING_LIKE_SERVICE_KEY ] = content_updates
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        service_keys_to_content_updates = {}
        
        content_updates = []
        
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.6, ( hash, ) ) ) )
        
        service_keys_to_content_updates[ TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ] = content_updates
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        tests = []
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 1.0, TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 0.0, TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'rated', TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'not rated', TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 0.6, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 1.0, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.6, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.4, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'rated', TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'not rated', TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_LOCAL, None, 0 ) )
        
        tests.append( ( ClientSearch.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        run_system_predicate_tests( tests )
        
    
    def test_file_system_predicates( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        result = self._read( 'file_system_predicates', CC.LOCAL_FILE_SERVICE_KEY )
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, min_current_count = 1 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX, min_current_count = 1 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE, min_current_count = 0 ) )
        predicates.extend( [ ClientSearch.Predicate( predicate_type ) for predicate_type in [ ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, ClientSearch.PREDICATE_TYPE_SYSTEM_DIMENSIONS, ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ClientSearch.PREDICATE_TYPE_SYSTEM_NOTES, ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS, ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS ] ] )
        
        self.assertEqual( set( result ), set( predicates ) )
        
        for i in range( len( predicates ) ): self.assertEqual( result[i].GetCount(), predicates[i].GetCount() )
        
    
    def test_file_updates( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = bytes.fromhex( 'fdadb2cae78f2dfeb629449cd005f2a2' )
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        hash_id = media_result.GetHashId()
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertFalse( locations_manager.IsLocal() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertTrue( locations_manager.IsLocal() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertTrue( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertTrue( locations_manager.IsLocal() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertTrue( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertTrue( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertTrue( locations_manager.IsLocal() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertTrue( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertFalse( locations_manager.IsLocal() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = bytes.fromhex( 'fdadb2cae78f2dfeb629449cd005f2a2' )
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        hash_id = media_result.GetHashId()
        
        self._db._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertFalse( locations_manager.IsLocal() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.COMBINED_LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
    
    def test_filter_existing_tags( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        #
        
        services = list( self._read( 'services' ) )
        
        new_service_key = HydrusData.GenerateKey()
        
        services.append( ClientServices.GenerateService( new_service_key, HC.LOCAL_TAG, 'new service' ) )
        
        empty_service_key = HydrusData.GenerateKey()
        
        services.append( ClientServices.GenerateService( empty_service_key, HC.LOCAL_TAG, 'empty service' ) )
        
        self._write( 'update_services', services )
        
        #
        
        service_keys_to_content_updates = {}
        
        content_updates = []
        
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'character:samus aran', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:metroid', ( hash, ) ) ) )
        
        service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = content_updates
        
        content_updates = []
        
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'clothing:bodysuit', ( hash, ) ) ) )
        
        service_keys_to_content_updates[ new_service_key ] = content_updates
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        result = self._read( 'filter_existing_tags', CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, { 'character:samus aran', 'series:metroid', 'clothing:bodysuit' } )
        
        self.assertEqual( result, { 'character:samus aran', 'series:metroid' } )
        
        result = self._read( 'filter_existing_tags', new_service_key, { 'character:samus aran', 'series:metroid', 'clothing:bodysuit' } )
        
        self.assertEqual( result, { 'clothing:bodysuit' } )
        
        result = self._read( 'filter_existing_tags', empty_service_key, { 'character:samus aran', 'series:metroid', 'clothing:bodysuit' } )
        
        self.assertEqual( result, set() )
        
    
    def test_gui_sessions( self ):
        
        page_containers = []
        hashes_to_page_data = {}
        
        #
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportGallery()
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportMultipleWatcher()
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        service_keys_to_tags = ClientTags.ServiceKeysToTags( { HydrusData.GenerateKey() : [ 'some', 'tags' ] } )
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportHDD( [ 'some', 'paths' ], FileImportOptions.FileImportOptions(), { 'paths' : service_keys_to_tags }, True )
        
        management_controller.GetVariable( 'hdd_import' ).PausePlay() # to stop trying to import 'some' 'paths'
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        management_controller = ClientGUIManagement.CreateManagementControllerImportSimpleDownloader()
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        management_controller = ClientGUIManagement.CreateManagementControllerPetitions( HG.test_controller.example_tag_repo_service_key )
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
        
        fsc = ClientSearch.FileSearchContext( location_search_context = location_search_context, predicates = [] )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'search', fsc, True )
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        tag_search_context = ClientSearch.TagSearchContext( service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY )
        
        location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
        
        fsc = ClientSearch.FileSearchContext( location_search_context = location_search_context, tag_search_context = tag_search_context, predicates = [] )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'search', fsc, False )
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [ HydrusData.GenerateKey() for i in range( 200 ) ] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
        
        fsc = ClientSearch.FileSearchContext( location_search_context = location_search_context, predicates = [ ClientSearch.SYSTEM_PREDICATE_ARCHIVE ] )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'files', fsc, True )
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
        
        fsc = ClientSearch.FileSearchContext( location_search_context = location_search_context, predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag', min_current_count = 1, min_pending_count = 3 ) ] )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'wew lad', fsc, True )
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        location_search_context = ClientSearch.LocationSearchContext( current_service_keys = [ CC.LOCAL_FILE_SERVICE_KEY ] )
        
        fsc = ClientSearch.FileSearchContext( location_search_context = location_search_context, predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.2, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ) ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ) ) ] )
        
        management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'files', fsc, True )
        
        page_name = management_controller.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( management_controller, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        top_notebook_container = ClientGUISession.GUISessionContainerPageNotebook( 'top notebook', page_containers = page_containers)
        
        session = ClientGUISession.GUISessionContainer( 'test_session', top_notebook_container = top_notebook_container, hashes_to_page_data = hashes_to_page_data )
        
        self.assertTrue( session.HasAllPageData() )
        
        self._write( 'serialisable', session )
        
        loaded_session = self._read( 'gui_session', 'test_session' )
        
        self.assertTrue( loaded_session.HasAllPageData() )
        
        page_names = []
        
        for page_container in loaded_session.GetTopNotebook().GetPageContainers():
            
            page_names.append( page_container.GetName() )
            
        
        self.assertEqual( page_names, [ 'gallery', 'watcher', 'import', 'simple downloader', 'example tag repo petitions', 'search', 'search', 'files', 'wew lad', 'files' ] )
        
        
    
    def test_import( self ):
        
        TestClientDB._clear_db()
        
        test_files = []
        
        test_files.append( ( 'muh_swf.swf', 'edfef9905fdecde38e0752a5b6ab7b6df887c3968d4246adc9cffc997e168cdf', 456774, HC.APPLICATION_FLASH, 400, 400, { 33 }, { 1 }, True, None ) )
        test_files.append( ( 'muh_mp4.mp4', '2fa293907144a046d043d74e9570b1c792cbfd77ee3f5c93b2b1a1cb3e4c7383', 570534, HC.VIDEO_MP4, 480, 480, { 6266, 6290 }, { 151 }, True, None ) )
        test_files.append( ( 'muh_mpeg.mpeg', 'aebb10aaf3b27a5878fd2732ea28aaef7bbecef7449eaa759421c4ba4efff494', 772096, HC.VIDEO_MPEG, 657, 480, { 3500 }, { 105 }, False, None ) ) # not actually 720, as this has mickey-mouse SAR, it turns out
        test_files.append( ( 'muh_webm.webm', '55b6ce9d067326bf4b2fbe66b8f51f366bc6e5f776ba691b0351364383c43fcb', 84069, HC.VIDEO_WEBM, 640, 360, { 4010 }, { 120 }, True, None ) )
        test_files.append( ( 'muh_jpg.jpg', '5d884d84813beeebd59a35e474fa3e4742d0f2b6679faa7609b245ddbbd05444', 42296, HC.IMAGE_JPEG, 392, 498, { None }, { None }, False, None ) )
        test_files.append( ( 'muh_png.png', 'cdc67d3b377e6e1397ffa55edc5b50f6bdf4482c7a6102c6f27fa351429d6f49', 31452, HC.IMAGE_PNG, 191, 196, { None }, { None }, False, None ) )
        test_files.append( ( 'muh_apng.png', '9e7b8b5abc7cb11da32db05671ce926a2a2b701415d1b2cb77a28deea51010c3', 616956, HC.IMAGE_APNG, 500, 500, { 3133, 1880, 1125, 1800 }, { 27, 47 }, False, None ) )
        test_files.append( ( 'muh_gif.gif', '00dd9e9611ebc929bfc78fde99a0c92800bbb09b9d18e0946cea94c099b211c2', 15660, HC.IMAGE_GIF, 329, 302, { 600 }, { 5 }, False, None ) )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        for ( filename, hex_hash, size, mime, width, height, durations, num_frames, has_audio, num_words ) in test_files:
            
            HG.test_controller.SetRead( 'hash_status', ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            
            path = os.path.join( HC.STATIC_DIR, 'testing', filename )
            
            hash = bytes.fromhex( hex_hash )
            
            file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
            
            file_import_job.GeneratePreImportHashAndStatus()
            
            file_import_job.GenerateInfo()
            
            file_import_status = self._write( 'import_file', file_import_job )
            
            written_status = file_import_status.status
            written_hash = file_import_job.GetHash()
            written_note = file_import_status.note
            
            self.assertEqual( written_status, CC.STATUS_SUCCESSFUL_AND_NEW )
            self.assertEqual( written_note, '' )
            self.assertEqual( file_import_job.GetHash(), hash )
            
            media_result = self._read( 'media_result', written_hash )
            
            ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
            
            ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_has_audio, mr_num_words ) = mr_file_info_manager.ToTuple()
            
            mr_inbox = mr_locations_manager.inbox
            
            now = HydrusData.GetNow()
            
            self.assertEqual( mr_hash, hash )
            self.assertEqual( mr_inbox, True )
            self.assertEqual( mr_size, size )
            self.assertEqual( mr_mime, mime )
            self.assertEqual( mr_width, width )
            self.assertEqual( mr_height, height )
            self.assertIn( mr_duration, durations )
            self.assertIn( mr_num_frames, num_frames )
            self.assertEqual( mr_has_audio, has_audio )
            self.assertEqual( mr_num_words, num_words )
            
        
    
    def test_import_folders( self ):
        
        import_folder_1 = ClientImportLocal.ImportFolder( 'imp 1', path = TestController.DB_DIR, mimes = HC.VIDEO, publish_files_to_popup_button = False )
        import_folder_2 = ClientImportLocal.ImportFolder( 'imp 2', path = TestController.DB_DIR, mimes = HC.IMAGES, period = 1200, publish_files_to_popup_button = False )
        
        #
        
        result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
        
        self.assertEqual( result, [] )
        
        #
        
        self._write( 'serialisable', import_folder_1 )
        self._write( 'serialisable', import_folder_2 )
        
        result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
        
        for item in result:
            
            self.assertEqual( type( item ), ClientImportLocal.ImportFolder )
            
        
        #
        
        self._write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, 'imp 2' )
        
        result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
        
        ( item, ) = result
        
        self.assertEqual( item.GetName(), 'imp 1' )
        
    
    def test_init( self ):
        
        self.assertTrue( os.path.exists( TestController.DB_DIR ) )
        
        self.assertTrue( os.path.exists( os.path.join( TestController.DB_DIR, 'client.db' ) ) )
        
        client_files_default = os.path.join( TestController.DB_DIR, 'client_files' )
        
        self.assertTrue( os.path.exists( client_files_default ) )
        
        for prefix in HydrusData.IterateHexPrefixes():
            
            for c in ( 'f', 't' ):
                
                dir = os.path.join( client_files_default, c + prefix )
                
                self.assertTrue( os.path.exists( dir ) )
                
            
        
    
    def test_hash_status( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = bytes.fromhex( 'fdadb2cae78f2dfeb629449cd005f2a2' )
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_UNKNOWN )
        self.assertEqual( written_hash, None )
        
        #
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        # would be redundant, but sometimes(?) triggers the 'it is missing from db' hook
        self.assertIn( written_status, ( CC.STATUS_UNKNOWN, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ) )
        self.assertEqual( written_hash, hash )
        if written_status == CC.STATUS_UNKNOWN:
            
            self.assertIn( 'already in the db', written_note )
            
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_DELETED )
        self.assertEqual( written_hash, hash )
        
        # now physical delete
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = bytes.fromhex( 'fdadb2cae78f2dfeb629449cd005f2a2' )
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_UNKNOWN )
        self.assertEqual( written_hash, None )
        
        #
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        # would be redundant, but sometimes(?) triggers the 'it is missing from db' hook
        self.assertIn( written_status, ( CC.STATUS_UNKNOWN, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ) )
        self.assertEqual( written_hash, hash )
        if written_status == CC.STATUS_UNKNOWN:
            
            self.assertIn( 'already in the db', written_note )
            
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_DELETED )
        self.assertEqual( written_hash, hash )
        
    
    def test_media_results( self ):
        
        TestClientDB._clear_db()
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        hash = file_import_job.GetHash()
        
        #
        
        media_result = self._read( 'media_result', hash )
        
        ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
        
        ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_has_audio, mr_num_words ) = mr_file_info_manager.ToTuple()
        
        mr_inbox = mr_locations_manager.inbox
        
        now = HydrusData.GetNow()
        
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_inbox, True )
        self.assertEqual( mr_size, 5270 )
        self.assertEqual( mr_mime, HC.IMAGE_PNG )
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_width, 200 )
        self.assertEqual( mr_height, 200 )
        self.assertEqual( mr_duration, None )
        self.assertEqual( mr_num_frames, None )
        self.assertEqual( mr_has_audio, False )
        self.assertEqual( mr_num_words, None )
        
        ( media_result, ) = self._read( 'media_results_from_ids', ( 1, ) )
        
        ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
        
        ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_has_audio, mr_num_words ) = mr_file_info_manager.ToTuple()
        
        mr_inbox = mr_locations_manager.inbox
        
        now = HydrusData.GetNow()
        
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_inbox, True )
        self.assertEqual( mr_size, 5270 )
        self.assertEqual( mr_mime, HC.IMAGE_PNG )
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_width, 200 )
        self.assertEqual( mr_height, 200 )
        self.assertEqual( mr_duration, None )
        self.assertEqual( mr_num_frames, None )
        self.assertEqual( mr_has_audio, False )
        self.assertEqual( mr_num_words, None )
        
    
    def test_nums_pending( self ):
        
        TestClientDB._clear_db()
        
        result = self._read( 'nums_pending' )
        
        self.assertEqual( result, {} )
        
        #
        
        services = list( self._read( 'services' ) )
        
        tag_sk = HydrusData.GenerateKey()
        file_sk = HydrusData.GenerateKey()
        ipfs_sk = HydrusData.GenerateKey()
        
        services.append( ClientServices.GenerateService( tag_sk, HC.TAG_REPOSITORY, 'test tag repo' ) )
        services.append( ClientServices.GenerateService( file_sk, HC.FILE_REPOSITORY, 'test file repo' ) )
        services.append( ClientServices.GenerateService( ipfs_sk, HC.IPFS, 'test ipfs' ) )
        
        self._write( 'update_services', services )
        
        #
        
        result = self._read( 'nums_pending' )
        
        expected_result = {
            tag_sk: {
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS : 0,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS : 0,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS : 0
            },
            file_sk: {
                HC.SERVICE_INFO_NUM_PENDING_FILES: 0,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES: 0
            },
            ipfs_sk: {
                HC.SERVICE_INFO_NUM_PENDING_FILES: 0,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES: 0
            }
        }
        
        self.assertEqual( result, expected_result )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 64 ) ]
        
        tags = [ 'this', 'is', 'a:test' ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, hashes ) ) for tag in tags ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 64 ) ]
        
        tags = [ 'bad tag', 'bad' ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, hashes ) ) for tag in tags ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( tag, hashes ), reason = 'yo' ) for tag in tags ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        pairs = [
            ( 'sib tag 1a', 'sib tag 1b' ),
            ( 'sib tag 2a', 'sib tag 2b' ),
            ( 'sib tag 3a', 'sib tag 3b' ),
            ( 'sib tag 4a', 'sib tag 4b' )
        ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PEND, pair, reason = 'good sibling m8' ) for pair in pairs ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        pairs = [
            ( 'samus aran', 'princess peach' ),
            ( 'lara croft', 'princess peach' )
        ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, pair ) for pair in pairs ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, pair, reason = 'mistake' ) for pair in pairs ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        pairs = [
            ( 'par tag 1a', 'par tag 1b' ),
            ( 'par tag 2a', 'par tag 2b' ),
            ( 'par tag 3a', 'par tag 3b' )
        ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PEND, pair, reason = 'good parent m8' ) for pair in pairs ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        pairs = [
            ( 'ayanami rei', 'zelda' )
        ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD, pair ) for pair in pairs ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION, pair, reason = 'mistake' ) for pair in pairs ]
        
        service_keys_to_content_updates = { tag_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 15 ) ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ]
        
        service_keys_to_content_updates = { file_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 20 ) ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ]
        
        service_keys_to_content_updates = { ipfs_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        test_files = {
            '5d884d84813beeebd59a35e474fa3e4742d0f2b6679faa7609b245ddbbd05444' : 'muh_jpg.jpg',
            'cdc67d3b377e6e1397ffa55edc5b50f6bdf4482c7a6102c6f27fa351429d6f49' : 'muh_png.png',
            '9e7b8b5abc7cb11da32db05671ce926a2a2b701415d1b2cb77a28deea51010c3' : 'muh_apng.png'
        }
        
        file_import_options = HG.client_controller.new_options.GetDefaultFileImportOptions( 'loud' )
        
        for ( hash, filename ) in test_files.items():
            
            HG.test_controller.SetRead( 'hash_status', ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            
            path = os.path.join( HC.STATIC_DIR, 'testing', filename )
            
            file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
            
            file_import_job.GeneratePreImportHashAndStatus()
            
            file_import_job.GenerateInfo()
            
            file_import_status = self._write( 'import_file', file_import_job )
            
        
        hashes = list( [ bytes.fromhex( hh ) for hh in test_files.keys() ] )
        
        media_results = self._read( 'media_results', hashes )
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( mr.GetFileInfoManager(), 100 ) ) for mr in media_results ]
        
        service_keys_to_content_updates = { file_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( mr.GetFileInfoManager(), os.urandom( 16 ).hex() ) ) for mr in media_results ]
        
        service_keys_to_content_updates = { ipfs_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = 'nope' ) ]
        
        service_keys_to_content_updates = { file_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes ) ]
        
        service_keys_to_content_updates = { ipfs_sk : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        result = self._read( 'nums_pending' )
        
        expected_result = {
            tag_sk: {
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS : 64 * 3,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS : 64 * 2,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS : 4,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS : 2,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS : 3,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS : 1
            },
            file_sk: {
                HC.SERVICE_INFO_NUM_PENDING_FILES: 15,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES: 3
            },
            ipfs_sk: {
                HC.SERVICE_INFO_NUM_PENDING_FILES: 20,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES: 3
            }
        }
        
        self.assertEqual( result, expected_result )
        
    
    def test_pending( self ):
        
        TestClientDB._clear_db()
        
        service_key = HydrusData.GenerateKey()
        
        services = self._read( 'services' )
        
        old_services = list( services )
        
        service = ClientServices.GenerateService( service_key, HC.TAG_REPOSITORY, 'new tag repo' )
        
        service._account._account_type = HydrusNetwork.AccountType.GenerateAdminAccountType( HC.TAG_REPOSITORY )
        
        services.append( service )
        
        self._write( 'update_services', services )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 64 ) ]
        
        tags = [ 'this', 'is', 'a:test' ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, hashes ) ) for tag in tags ]
        
        service_keys_to_content_updates = { service_key : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        result = self._read( 'pending', service_key, ( HC.CONTENT_TYPE_MAPPINGS, ) )
        
        self.assertIsInstance( result, HydrusNetwork.ClientToServerUpdate )
        
        self.assertTrue( result.HasContent() )
        
        self.assertEqual( set( result.GetHashes() ), set( hashes ) )
        
        #
        
        TestClientDB._clear_db()
        
    
    def test_pixiv_account( self ):
        
        result = self._read( 'serialisable_simple', 'pixiv_account' )
        
        self.assertEqual( result, None )
        
        pixiv_id = 123456
        password = 'password'
        
        self._write( 'serialisable_simple', 'pixiv_account', ( pixiv_id, password ) )
        
        result = self._read( 'serialisable_simple', 'pixiv_account' )
        
        self.assertEqual( result, [ pixiv_id, password ] )
        
    
    def test_services( self ):
        
        TestClientDB._clear_db()
        
        result = self._read( 'services', ( HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_TRASH_DOMAIN, HC.COMBINED_LOCAL_FILE, HC.LOCAL_TAG, HC.LOCAL_RATING_LIKE ) )
        
        result_service_keys = { service.GetServiceKey() for service in result }
        
        self.assertEqual( { CC.TRASH_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, CC.LOCAL_UPDATE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY, CC.DEFAULT_FAVOURITES_RATING_SERVICE_KEY }, result_service_keys )
        
        #
        
        result = self._read( 'service_info', CC.LOCAL_FILE_SERVICE_KEY )
        
        self.assertEqual( type( result ), dict )
        
        for ( k, v ) in list(result.items()):
            
            self.assertEqual( type( k ), int )
            self.assertEqual( type( v ), int )
            
        
        #
        
        NUM_DEFAULT_SERVICES = 13
        
        services = self._read( 'services' )
        
        self.assertEqual( len( services ), NUM_DEFAULT_SERVICES )
        
        old_services = list( services )
        
        services.append( ClientServices.GenerateService( HydrusData.GenerateKey(), HC.TAG_REPOSITORY, 'new service' ) )
        
        self._write( 'update_services', services )
        
        services = self._read( 'services' )
        
        self.assertEqual( len( services ), NUM_DEFAULT_SERVICES + 1 )
        
        self._write( 'update_services', old_services )
        
        services = self._read( 'services' )
        
        self.assertEqual( len( services ), NUM_DEFAULT_SERVICES )
        
    
    def test_shortcuts( self ):
        
        num_default = len( ClientDefaults.GetDefaultShortcuts() )
        
        result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
        
        self.assertEqual( len( result ), num_default )
        
        #
        
        for ( i, shortcuts ) in enumerate( ClientDefaults.GetDefaultShortcuts() ):
            
            name = 'shortcuts ' + str( i )
            
            shortcuts.SetName( name )
            
            self._write( 'serialisable', shortcuts )
            
            result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
            
            self.assertEqual( len( result ), num_default + 1 )
            
            result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET, name )
            
            for ( shortcut, command ) in shortcuts:
                
                self.assertEqual( tuple( result.GetCommand( shortcut )._data ), tuple( command._data ) )
                
            
            #
            
            self._write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET, name )
            
            result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
            
            self.assertEqual( len( result ), num_default )
            
        
    
