from . import ClientConstants as CC
from . import ClientData
from . import ClientDB
from . import ClientDefaults
from . import ClientDownloading
from . import ClientExporting
from . import ClientFiles
from . import ClientGUIManagement
from . import ClientGUIPages
from . import ClientImporting
from . import ClientImportLocal
from . import ClientImportOptions
from . import ClientImportFileSeeds
from . import ClientRatings
from . import ClientSearch
from . import ClientServices
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusVideoHandling
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusSerialisable
import itertools
import os
from . import ServerDB
import shutil
import sqlite3
import stat
from . import TestController
import time
import threading
import unittest
import wx

class TestClientDB( unittest.TestCase ):
    
    @classmethod
    def _clear_db( cls ):
        
        cls._delete_db()
        
        # class variable
        cls._db = ClientDB.DB( HG.test_controller, TestController.DB_DIR, 'client' )
        
    
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
        
    
    @classmethod
    def setUpClass( cls ):
        
        cls._db = ClientDB.DB( HG.test_controller, TestController.DB_DIR, 'client' )
        
        HG.test_controller.SetRead( 'hash_status', ( CC.STATUS_UNKNOWN, None, '' ) )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._delete_db()
        
    
    def _read( self, action, *args, **kwargs ): return TestClientDB._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestClientDB._db.Write( action, True, *args, **kwargs )
    
    def test_autocomplete( self ):
        
        TestClientDB._clear_db()
        
        result = self._read( 'autocomplete_predicates', tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, search_text = 'c*' )
        
        self.assertEqual( result, [] )
        
        result = self._read( 'autocomplete_predicates', tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, search_text = 'series:*' )
        
        self.assertEqual( result, [] )
        
        #
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_import_job = ClientImportFileSeeds.FileImportJob( path )
        
        file_import_job.GenerateHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        service_keys_to_content_updates = {}
        
        content_updates = []

        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
        service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = content_updates
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        # cars
        
        result = self._read( 'autocomplete_predicates', tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, search_text = 'c*', add_namespaceless = True )
        
        preds = set()
        
        preds.add( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'car', min_current_count = 1 ) )
        preds.add( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        # cars
        
        result = self._read( 'autocomplete_predicates', tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, search_text = 'c*', add_namespaceless = False )
        
        preds = set()
        
        preds.add( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 ) )
        preds.add( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'car', min_current_count = 1 ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, search_text = 'ser*' )
        
        self.assertEqual( result, [] )
        
        #
        
        result = self._read( 'autocomplete_predicates', tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, search_text = 'series:c*' )
        
        pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'series:cars', min_current_count = 1 )
        
        ( read_pred, ) = result
        
        self.assertEqual( read_pred.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_predicates', tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, search_text = 'car', exact_match = True )
        
        pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'car', min_current_count = 1 )
        
        ( read_pred, ) = result
        
        self.assertEqual( read_pred.GetCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_predicates', tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, search_text = 'c', exact_match = True )
        
        self.assertEqual( result, [] )
        
    
    def test_export_folders( self ):
        
        file_search_context = ClientSearch.FileSearchContext(file_service_key = HydrusData.GenerateKey(), tag_service_key = HydrusData.GenerateKey(), predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'test' ) ] )
        
        export_folder = ClientExporting.ExportFolder( 'test path', export_type = HC.EXPORT_FOLDER_TYPE_REGULAR, delete_from_client_after_export = False, file_search_context = file_search_context, period = 3600, phrase = '{hash}' )
        
        self._write( 'serialisable', export_folder )
        
        [ result ] = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
        
        self.assertEqual( result.GetName(), export_folder.GetName() )
        
    
    def test_file_query_ids( self ):
        
        TestClientDB._clear_db()
        
        def run_namespace_predicate_tests( tests ):
            
            for ( inclusive, namespace, result ) in tests:
                
                predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_NAMESPACE, namespace, inclusive ) ]
                
                search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_system_predicate_tests( tests ):
            
            for ( predicate_type, info, result ) in tests:
                
                predicates = [ ClientSearch.Predicate( predicate_type, info ) ]
                
                search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_tag_predicate_tests( tests ):
            
            for ( inclusive, tag, result ) in tests:
                
                predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive ) ]
                
                search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_or_predicate_tests( tests ):
            
            for ( predicates, result ) in tests:
                
                search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        tests = []
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_LOCAL, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_import_job = ClientImportFileSeeds.FileImportJob( path )
        
        file_import_job.GenerateHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        ( written_status, written_note ) = self._write( 'import_file', file_import_job )
        
        self.assertEqual( written_status, CC.STATUS_SUCCESSFUL_AND_NEW )
        self.assertEqual( written_note, '' )
        self.assertEqual( file_import_job.GetHash(), hash )
        
        time.sleep( 1 )
        
        #
        
        tests = []
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 1, 1, 1, 1, ) ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 0, 0, ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_AGE, ( '\u2248', 'delta', ( 1, 1, 1, 1, ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_AGE, ( '\u2248', 'delta', ( 0, 0, 0, 0, ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 'delta', ( 1, 1, 1, 1, ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 'delta', ( 0, 0, 0, 0, ) ), 1 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '<', 100, ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '<', 0, ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '\u2248', 100, ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '\u2248', 0, ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '=', 100, ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '=', 0, ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '>', 100, ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '>', 0, ), 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 1 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HASH, ( hash, 'sha256' ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HASH, ( bytes.fromhex( '0123456789abcdef' * 4 ), 'sha256' ), 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 201 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 200 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '\u2248', 200 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '\u2248', 60 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '\u2248', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '=', 200 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '=', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '>', 200 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '>', 199 ), 1 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_INBOX, None, 1 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_LOCAL, None, 1 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_MIME, HC.IMAGES, 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_MIME, ( HC.IMAGE_PNG, ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_MIME, ( HC.IMAGE_JPEG, ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_MIME, HC.VIDEO, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '<', 1 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '=', 0 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '=', 1 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '>', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '>', 1 ), 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '<', 1 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '\u2248', 0 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '\u2248', 1 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '=', 0 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '=', 1 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '>', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '>', 1 ), 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 1, 1 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 4, 3 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATIO, ( '\u2248', 1, 1 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATIO, ( '\u2248', 200, 201 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATIO, ( '\u2248', 4, 1 ), 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( hash, 5 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( bytes.fromhex( '0123456789abcdef' * 4 ), 5 ), 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 0, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 5270, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 5271, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '=', 5270, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '=', 0, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '\u2248', 5270, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '\u2248', 0, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5270, HydrusData.ConvertUnitToInt( 'B' ) ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5269, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusData.ConvertUnitToInt( 'B' ) ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusData.ConvertUnitToInt( 'KB' ) ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusData.ConvertUnitToInt( 'MB' ) ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusData.ConvertUnitToInt( 'GB' ) ), 1 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '<', 201 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '<', 200 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '<', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '\u2248', 200 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '\u2248', 60 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '\u2248', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 200 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '>', 200 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '>', 199 ), 1 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_LIMIT, 100, 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_LIMIT, 1, 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_LIMIT, 0, 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        service_keys_to_content_updates = {}
        
        service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( hash, ) ), )
        service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ), )
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 1 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '<', 2 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '<', 1 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '=', 0 ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '=', 1 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '>', 0 ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '>', 1 ), 0 ) )
        
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
        
        service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = content_updates
        
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
        
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 201 ) ) )
        
        or_pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'truck' ) )
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 0 ) )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'truck', inclusive = False ) )
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'truck' ) )
        
        or_pred_1 = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        preds = []
        
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'maker:toyota' ) )
        preds.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'maker:ford' ) )
        
        or_pred_2 = ClientSearch.Predicate( HC.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred_1, or_pred_2 ], 1 ) )
        
        run_or_predicate_tests( tests )
        
        #
        
        from . import TestController
        
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
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 1.0, TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 0.0, TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'rated', TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'not rated', TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 0.6, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 1.0, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.6, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.4, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'rated', TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'not rated', TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_LOCAL, None, 0 ) )
        
        tests.append( ( HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        run_system_predicate_tests( tests )
        
    
    def test_file_system_predicates( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_import_job = ClientImportFileSeeds.FileImportJob( path )
        
        file_import_job.GenerateHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        result = self._read( 'file_system_predicates', CC.LOCAL_FILE_SERVICE_KEY )
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING, min_current_count = 1 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_INBOX, min_current_count = 1 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, min_current_count = 0 ) )
        predicates.extend( [ ClientSearch.Predicate( predicate_type ) for predicate_type in [ HC.PREDICATE_TYPE_SYSTEM_UNTAGGED, HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, HC.PREDICATE_TYPE_SYSTEM_LIMIT, HC.PREDICATE_TYPE_SYSTEM_SIZE, HC.PREDICATE_TYPE_SYSTEM_AGE, HC.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, HC.PREDICATE_TYPE_SYSTEM_HASH, HC.PREDICATE_TYPE_SYSTEM_DIMENSIONS, HC.PREDICATE_TYPE_SYSTEM_DURATION, HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, HC.PREDICATE_TYPE_SYSTEM_MIME, HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, HC.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, HC.PREDICATE_TYPE_SYSTEM_DUPLICATE_RELATIONSHIP_COUNT, HC.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS ] ] )
        
        self.assertEqual( set( result ), set( predicates ) )
        
        for i in range( len( predicates ) ): self.assertEqual( result[i].GetCount(), predicates[i].GetCount() )
        
    
    def test_gui_sessions( self ):
        
        def wx_code():
            
            test_frame = TestController.TestFrame()
            
            try:
                
                session = ClientGUIPages.GUISession( 'test_session' )
                
                #
                
                management_controller = ClientGUIManagement.CreateManagementControllerImportGallery()
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                management_controller = ClientGUIManagement.CreateManagementControllerImportMultipleWatcher()
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                service_keys_to_tags = ClientTags.ServiceKeysToTags( { HydrusData.GenerateKey() : [ 'some', 'tags' ] } )
                
                management_controller = ClientGUIManagement.CreateManagementControllerImportHDD( [ 'some', 'paths' ], ClientImportOptions.FileImportOptions(), { 'paths' : service_keys_to_tags }, True )
                
                management_controller.GetVariable( 'hdd_import' ).PausePlay() # to stop trying to import 'some' 'paths'
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                management_controller = ClientGUIManagement.CreateManagementControllerImportSimpleDownloader()
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                management_controller = ClientGUIManagement.CreateManagementControllerPetitions( HG.test_controller.example_tag_repo_service_key )
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                fsc = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [] )
                
                management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'search', CC.LOCAL_FILE_SERVICE_KEY, fsc, True )
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                fsc = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, tag_service_key = CC.LOCAL_TAG_SERVICE_KEY, predicates = [] )
                
                management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'search', CC.LOCAL_FILE_SERVICE_KEY, fsc, False )
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [ HydrusData.GenerateKey() for i in range( 200 ) ] )
                
                session.AddPageTuple( page )
                
                #
                
                fsc = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [ ClientSearch.SYSTEM_PREDICATE_ARCHIVE ] )
                
                management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'files', CC.LOCAL_FILE_SERVICE_KEY, fsc, True )
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                fsc = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'tag', min_current_count = 1, min_pending_count = 3 ) ] )
                
                management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'wew lad', CC.LOCAL_FILE_SERVICE_KEY, fsc, True )
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                fsc = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.2, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ) ), ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ) ) ] )
                
                management_controller = ClientGUIManagement.CreateManagementControllerQuery( 'files', CC.LOCAL_FILE_SERVICE_KEY, fsc, True )
                
                page = ClientGUIPages.Page( test_frame, HG.test_controller, management_controller, [] )
                
                session.AddPageTuple( page )
                
                #
                
                self._write( 'serialisable', session )
                
                result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_GUI_SESSION, 'test_session' )
                
                page_names = []
                
                for ( page_type, page_data ) in result.GetPageTuples():
                    
                    if page_type == 'page':
                        
                        ( management_controller, initial_hashes ) = page_data
                        
                        page_names.append( management_controller.GetPageName() )
                        
                    
                
                self.assertEqual( page_names, [ 'gallery', 'watcher', 'import', 'simple downloader', 'example tag repo petitions', 'search', 'search', 'files', 'wew lad', 'files' ] )
                
            finally:
                
                test_frame.DestroyLater()
                
            
        
        HG.test_controller.CallBlockingToWX( HG.test_controller.win, wx_code )
        
    
    def test_import( self ):
        
        TestClientDB._clear_db()
        
        test_files = []
        
        test_files.append( ( 'muh_swf.swf', 'edfef9905fdecde38e0752a5b6ab7b6df887c3968d4246adc9cffc997e168cdf', 456774, HC.APPLICATION_FLASH, 400, 400, { 33 }, { 1 }, None ) )
        test_files.append( ( 'muh_mp4.mp4', '2fa293907144a046d043d74e9570b1c792cbfd77ee3f5c93b2b1a1cb3e4c7383', 570534, HC.VIDEO_MP4, 480, 480, { 6266, 6290 }, { 151 }, None ) )
        test_files.append( ( 'muh_mpeg.mpeg', 'aebb10aaf3b27a5878fd2732ea28aaef7bbecef7449eaa759421c4ba4efff494', 772096, HC.VIDEO_MPEG, 720, 480, { 3500 }, { 105 }, None ) )
        test_files.append( ( 'muh_webm.webm', '55b6ce9d067326bf4b2fbe66b8f51f366bc6e5f776ba691b0351364383c43fcb', 84069, HC.VIDEO_WEBM, 640, 360, { 4010 }, { 120 }, None ) )
        test_files.append( ( 'muh_jpg.jpg', '5d884d84813beeebd59a35e474fa3e4742d0f2b6679faa7609b245ddbbd05444', 42296, HC.IMAGE_JPEG, 392, 498, { None }, { None }, None ) )
        test_files.append( ( 'muh_png.png', 'cdc67d3b377e6e1397ffa55edc5b50f6bdf4482c7a6102c6f27fa351429d6f49', 31452, HC.IMAGE_PNG, 191, 196, { None }, { None }, None ) )
        test_files.append( ( 'muh_apng.png', '9e7b8b5abc7cb11da32db05671ce926a2a2b701415d1b2cb77a28deea51010c3', 616956, HC.IMAGE_APNG, 500, 500, { 3133, 1880, 1125, 1800 }, { 27, 47 }, None ) )
        test_files.append( ( 'muh_gif.gif', '00dd9e9611ebc929bfc78fde99a0c92800bbb09b9d18e0946cea94c099b211c2', 15660, HC.IMAGE_GIF, 329, 302, { 600 }, { 5 }, None ) )
        
        for ( filename, hex_hash, size, mime, width, height, durations, nums_frame, num_words ) in test_files:
            
            path = os.path.join( HC.STATIC_DIR, 'testing', filename )
            
            hash = bytes.fromhex( hex_hash )
            
            file_import_job = ClientImportFileSeeds.FileImportJob( path )
            
            file_import_job.GenerateHashAndStatus()
            
            file_import_job.GenerateInfo()
            
            ( written_status, written_note ) = self._write( 'import_file', file_import_job )
            
            self.assertEqual( written_status, CC.STATUS_SUCCESSFUL_AND_NEW )
            self.assertEqual( written_note, '' )
            self.assertEqual( file_import_job.GetHash(), hash )
            
            file_import_job = ClientImportFileSeeds.FileImportJob( path )
            
            file_import_job.GenerateHashAndStatus()
            
            file_import_job.GenerateInfo()
            
            ( written_status, written_note ) = self._write( 'import_file', file_import_job )
            
            # would be redundant, but triggers the 'it is missing from db' hook
            self.assertEqual( written_status, CC.STATUS_SUCCESSFUL_AND_NEW )
            self.assertIn( 'already in the db', written_note )
            self.assertEqual( file_import_job.GetHash(), hash )
            
            written_hash = file_import_job.GetHash()
            
            ( media_result, ) = self._read( 'media_results', ( written_hash, ) )
            
            ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
            
            ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words ) = mr_file_info_manager.ToTuple()
            
            mr_inbox = mr_locations_manager.GetInbox()
            
            now = HydrusData.GetNow()
            
            self.assertEqual( mr_hash, hash )
            self.assertEqual( mr_inbox, True )
            self.assertEqual( mr_size, size )
            self.assertEqual( mr_mime, mime )
            self.assertEqual( mr_width, width )
            self.assertEqual( mr_height, height )
            self.assertIn( mr_duration, durations )
            self.assertIn( mr_num_frames, nums_frame )
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
        
        result = self._read( 'hash_status', 'md5', md5 )
        
        self.assertEqual( result, ( CC.STATUS_UNKNOWN, None, '' ) )
        
        #
        
        file_import_job = ClientImportFileSeeds.FileImportJob( path )
        
        file_import_job.GenerateHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        ( status, written_hash, note ) = self._read( 'hash_status', 'md5', md5 )
        
        # would be redundant, but sometimes(?) triggers the 'it is missing from db' hook
        self.assertIn( status, ( CC.STATUS_UNKNOWN, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ) )
        self.assertEqual( written_hash, hash )
        if status == CC.STATUS_UNKNOWN:
            
            self.assertIn( 'already in the db', note )
            
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        ( status, hash, note ) = self._read( 'hash_status', 'md5', md5 )
        
        self.assertEqual( ( status, hash ), ( CC.STATUS_DELETED, hash ) )
        
    
    def test_media_results( self ):
        
        TestClientDB._clear_db()
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_import_job = ClientImportFileSeeds.FileImportJob( path )
        
        file_import_job.GenerateHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        hash = file_import_job.GetHash()
        
        #
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
        
        ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words ) = mr_file_info_manager.ToTuple()
        
        mr_inbox = mr_locations_manager.GetInbox()
        
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
        self.assertEqual( mr_num_words, None )
        
        ( media_result, ) = self._read( 'media_results_from_ids', ( 1, ) )
        
        ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
        
        ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words ) = mr_file_info_manager.ToTuple()
        
        mr_inbox = mr_locations_manager.GetInbox()
        
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
        self.assertEqual( mr_num_words, None )
        
    
    def test_tag_censorship( self ):
        
        result = self._read( 'tag_censorship' )
        
        self.assertEqual( result, [] )
        
        result = self._read( 'tag_censorship', CC.LOCAL_TAG_SERVICE_KEY )
        
        self.assertEqual( result, ( True, [] ) )
        
        #
        
        info = []
        
        info.append( ( CC.LOCAL_TAG_SERVICE_KEY, False, [ ':', 'series:' ] ) )
        info.append( ( CC.LOCAL_FILE_SERVICE_KEY, True, [ ':' ] ) ) # bit dodgy, but whatever!
        
        self._write( 'tag_censorship', info )
        
        #
        
        result = self._read( 'tag_censorship' )
        
        self.assertEqual( len( result ), len( info ) )
        
        for row in result:
            
            self.assertIn( row, info )
            
        
        result = self._read( 'tag_censorship', CC.LOCAL_TAG_SERVICE_KEY )
        
        self.assertEqual( result, ( False, [ ':', 'series:' ] ) )
        
    
    def test_nums_pending( self ):
        
        result = self._read( 'nums_pending' )
        
        self.assertEqual( result, {} )
        
        # we can do more testing when I add repo service to this testing framework
        
    
    def test_pending( self ):
        
        service_key = HydrusData.GenerateKey()
        
        services = self._read( 'services' )
        
        old_services = list( services )
        
        services.append( ClientServices.GenerateService( service_key, HC.TAG_REPOSITORY, 'new tag repo' ) )
        
        self._write( 'update_services', services )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 64 ) ]
        
        tags = [ 'this', 'is', 'a:test' ]
        
        content_updates = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, hashes ) ) for tag in tags ]
        
        service_keys_to_content_updates = { service_key : content_updates }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        result = self._read( 'pending', service_key )
        
        self.assertIsInstance( result, HydrusNetwork.ClientToServerUpdate )
        
        self.assertTrue( result.HasContent() )
        
        self.assertEqual( set( result.GetHashes() ), set( hashes ) )
        
        #
        
        self._write( 'update_services', old_services )
        
    
    def test_pixiv_account( self ):
        
        result = self._read( 'serialisable_simple', 'pixiv_account' )
        
        self.assertEqual( result, None )
        
        pixiv_id = 123456
        password = 'password'
        
        self._write( 'serialisable_simple', 'pixiv_account', ( pixiv_id, password ) )
        
        result = self._read( 'serialisable_simple', 'pixiv_account' )
        
        self.assertTrue( result, ( pixiv_id, password ) )
        
    
    def test_repo_downloads( self ):
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, set() )
        
        #
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        service_keys_to_content_updates = {}
        
        service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, ( hash, ) ), )
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, { hash } )
        
        #
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        service_keys_to_content_updates = {}
        
        service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PEND, ( hash, ) ), )
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, set() )
        
    
    def test_services( self ):
        
        result = self._read( 'services', ( HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_TRASH_DOMAIN, HC.COMBINED_LOCAL_FILE, HC.LOCAL_TAG ) )
        
        result_service_keys = { service.GetServiceKey() for service in result }
        
        self.assertEqual( { CC.TRASH_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, CC.LOCAL_UPDATE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_SERVICE_KEY, CC.LOCAL_TAG_SERVICE_KEY }, result_service_keys )
        
        #
        
        result = self._read( 'service_info', CC.LOCAL_FILE_SERVICE_KEY )
        
        self.assertEqual( type( result ), dict )
        
        for ( k, v ) in list(result.items()):
            
            self.assertEqual( type( k ), int )
            self.assertEqual( type( v ), int )
            
        
        #
        
        NUM_DEFAULT_SERVICES = 10
        
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
                
                self.assertEqual( result.GetCommand( shortcut ).GetData(), command.GetData() )
                
            
            #
            
            self._write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET, name )
            
            result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
            
            self.assertEqual( len( result ), num_default )
            
        
    
