import ClientConstants as CC
import ClientData
import ClientDB
import ClientDefaults
import collections
import HydrusConstants as HC
import HydrusExceptions
import itertools
import os
import ServerDB
import shutil
import sqlite3
import stat
import TestConstants
import tempfile
import time
import threading
import unittest
import yaml
import HydrusData
import ClientSearch
import HydrusNetworking

class TestClientDB( unittest.TestCase ):
    
    def _clear_db( self ):
        
        db = sqlite3.connect( self._db._db_path, isolation_level = None, detect_types = sqlite3.PARSE_DECLTYPES )
        
        c = db.cursor()
        
        c.execute( 'DELETE FROM files_info;' )
        c.execute( 'DELETE FROM mappings;' )
        
    
    def _read( self, action, *args, **kwargs ): return self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return self._db.Write( action, HC.HIGH_PRIORITY, True, *args, **kwargs )
    
    @classmethod
    def setUpClass( self ):
        
        self._old_db_dir = HC.DB_DIR
        self._old_client_files_dir = HC.CLIENT_FILES_DIR
        self._old_client_thumbnails_dir = HC.CLIENT_THUMBNAILS_DIR
        
        HC.DB_DIR = tempfile.mkdtemp()
        
        HC.CLIENT_FILES_DIR = HC.DB_DIR + os.path.sep + 'client_files'
        HC.CLIENT_THUMBNAILS_DIR = HC.DB_DIR + os.path.sep + 'client_thumbnails'
        
        if not os.path.exists( HC.DB_DIR ): os.mkdir( HC.DB_DIR )
        
        self._db = ClientDB.DB()
        
        threading.Thread( target = self._db.MainLoop, name = 'Database Main Loop' ).start()
        
    
    @classmethod
    def tearDownClass( self ):
        
        self._db.Shutdown()
        
        while not self._db.LoopIsFinished(): time.sleep( 0.1 )
        
        def make_temp_files_deletable( function_called, path, traceback_gumpf ):
            
            os.chmod( path, stat.S_IWRITE )
            
            try: function_called( path ) # try again
            except: pass
            
        
        if os.path.exists( HC.DB_DIR ): shutil.rmtree( HC.DB_DIR, onerror = make_temp_files_deletable )
        
        HC.DB_DIR = self._old_db_dir
        HC.CLIENT_FILES_DIR = self._old_client_files_dir
        HC.CLIENT_THUMBNAILS_DIR = self._old_client_thumbnails_dir
        
    
    def test_4chan_pass( self ):
        
        result = self._read( '4chan_pass' )
        
        self.assertTrue( result, ( '', '', 0 ) )
        
        token = 'token'
        pin = 'pin'
        timeout = HydrusData.GetNow() + 100000
        
        self._write( '4chan_pass', ( token, pin, timeout ) )
        
        result = self._read( '4chan_pass' )
        
        self.assertTrue( result, ( token, pin, timeout ) )
        
    
    def test_autocomplete( self ):
        
        self._clear_db()
        
        result = self._read( 'autocomplete_predicates', half_complete_tag = 'c' )
        
        self.assertEqual( result, [] )
        
        result = self._read( 'autocomplete_predicates', half_complete_tag = 'series:' )
        
        self.assertEqual( result, [] )
        
        #
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        self._write( 'import_file', path )
        
        #
        
        service_keys_to_content_updates = {}
        
        content_updates = []

        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
        service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = content_updates
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        # cars
        
        result = self._read( 'autocomplete_predicates', half_complete_tag = 'c', add_namespaceless = True )
        
        preds = set()
        
        preds.add( HydrusData.Predicate( HC.PREDICATE_TYPE_TAG, 'car', counts = { HC.CURRENT : 1 } ) )
        preds.add( HydrusData.Predicate( HC.PREDICATE_TYPE_TAG, 'series:cars', counts = { HC.CURRENT : 1 } ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        # cars
        
        result = self._read( 'autocomplete_predicates', half_complete_tag = 'c', add_namespaceless = False )
        
        preds = set()
        
        preds.add( HydrusData.Predicate( HC.PREDICATE_TYPE_TAG, 'series:cars', counts = { HC.CURRENT : 1 } ) )
        preds.add( HydrusData.Predicate( HC.PREDICATE_TYPE_TAG, 'car', counts = { HC.CURRENT : 1 } ) )
        
        for p in result: self.assertEqual( p.GetCount( HC.CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', half_complete_tag = 'ser' )
        
        self.assertEqual( result, [] )
        
        #
        
        result = self._read( 'autocomplete_predicates', half_complete_tag = 'series:c' )
        
        pred = HydrusData.Predicate( HC.PREDICATE_TYPE_TAG, 'series:cars', counts = { HC.CURRENT : 1 } )
        
        ( read_pred, ) = result
        
        self.assertEqual( read_pred.GetCount( HC.CURRENT ), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_predicates', tag = 'car' )
        
        pred = HydrusData.Predicate( HC.PREDICATE_TYPE_TAG, 'car', counts = { HC.CURRENT : 1 } )
        
        ( read_pred, ) = result
        
        self.assertEqual( read_pred.GetCount( HC.CURRENT ), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_predicates', tag = 'c' )
        
        self.assertEqual( result, [] )
        
    
    def test_booru( self ):
        
        default_boorus = ClientDefaults.GetDefaultBoorus()
        
        for ( name, booru ) in default_boorus.items():
            
            read_booru = self._read( 'remote_booru', name )
            
            self.assertEqual( booru.GetData(), read_booru.GetData() )
            
        
        #
        
        result = self._read( 'remote_boorus' )
        
        for ( name, booru ) in default_boorus.items(): self.assertEqual( result[ name ].GetData(), booru.GetData() )
        
        #
    
        name = 'blah'
        search_url = 'url'
        search_separator = '%20'
        advance_by_page_num = True
        thumb_classname = 'thumb'
        image_id = None
        image_data = 'Download'
        tag_classnames_to_namespaces = { 'tag' : '' }
        
        booru = ClientData.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
        
        self._write( 'remote_booru', 'blah', booru )
        
        read_booru = self._read( 'remote_booru', name )
        
        self.assertEqual( booru.GetData(), read_booru.GetData() )
        
        #
        
        self._write( 'delete_remote_booru', 'blah' )
        
        with self.assertRaises( Exception ):
            
            read_booru = self._read( 'remote_booru', name )
            
        
    
    def test_downloads( self ):
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, set() )
        
        #
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        service_keys_to_content_updates = {}
        
        service_keys_to_content_updates[ CC.LOCAL_FILE_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PENDING, ( hash, ) ), )
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, { hash } )
        
        #
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        service_keys_to_content_updates = {}
        
        service_keys_to_content_updates[ CC.LOCAL_FILE_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PENDING, ( hash, ) ), )
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, set() )
        
    
    def test_favourite_custom_filter_actions( self ):
        
        result = self._read( 'favourite_custom_filter_actions' )
        
        self.assertEqual( result, dict() )
        
        #
        
        favourite_custom_filter_actions = { 'a' : 'blah', 'b' : 'bleh' }
        
        for ( name, actions ) in favourite_custom_filter_actions.items(): self._write( 'favourite_custom_filter_actions', name, actions )
        
        self._write( 'favourite_custom_filter_actions', 'c', 'bluh' )
        
        self._write( 'delete_favourite_custom_filter_actions', 'c' )
        
        #
        
        result = self._read( 'favourite_custom_filter_actions' )
        
        self.assertEqual( result, favourite_custom_filter_actions )
        
    
    def test_file_query_ids( self ):
        
        self._clear_db()
        
        def run_namespace_predicate_tests( tests ):
            
            for ( inclusive, namespace, result ) in tests:
                
                predicates = [ HydrusData.Predicate( HC.PREDICATE_TYPE_NAMESPACE, namespace, inclusive = inclusive ) ]
                
                search_context = ClientData.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_system_predicate_tests( tests ):
            
            for ( predicate_type, info, result ) in tests:
                
                predicates = [ HydrusData.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( predicate_type, info ) ) ]
                
                search_context = ClientData.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_tag_predicate_tests( tests ):
            
            for ( inclusive, tag, result ) in tests:
                
                predicates = [ HydrusData.Predicate( HC.PREDICATE_TYPE_TAG, tag, inclusive = inclusive ) ]
                
                search_context = ClientData.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        tests = []
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LOCAL, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None, 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        self._write( 'import_file', path )
        
        time.sleep( 1 )
        
        #
        
        tests = []
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( '<', 1, 1, 1, 1, ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( '<', 0, 0, 0, 0, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( u'\u2248', 1, 1, 1, 1, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( u'\u2248', 0, 0, 0, 0, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( '>', 1, 1, 1, 1, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_AGE, ( '>', 0, 0, 0, 0, ), 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '<', 100, ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '<', 0, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( u'\u2248', 100, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( u'\u2248', 0, ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '=', 100, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '=', 0, ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '>', 100, ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_DURATION, ( '>', 0, ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None, 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( False, HC.CURRENT, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( False, HC.PENDING, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( True, HC.CURRENT, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( True, HC.PENDING, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HASH, hash, 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HASH, ( '0123456789abcdef' * 4 ).decode( 'hex' ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '<', 201 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '<', 200 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( u'\u2248', 200 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( u'\u2248', 60 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( u'\u2248', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '=', 200 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '=', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '>', 200 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_HEIGHT, ( '>', 199 ), 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None, 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LOCAL, None, 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_MIME, HC.IMAGES, 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_MIME, HC.IMAGE_PNG, 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_MIME, HC.IMAGE_JPEG, 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_MIME, HC.VIDEO, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 0 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 1 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '>', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '>', 1 ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '<', 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( u'\u2248', 0 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( u'\u2248', 1 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '=', 0 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '=', 1 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '>', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, ( '>', 1 ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( '=', 1, 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( '=', 4, 3 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( u'\u2248', 1, 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( u'\u2248', 200, 201 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_RATIO, ( u'\u2248', 4, 1 ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, ( hash, 5 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, ( ( '0123456789abcdef' * 4 ).decode( 'hex' ), 5 ), 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 0, HydrusData.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 5270, HydrusData.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 5271, HydrusData.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '=', 5270, HydrusData.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '=', 0, HydrusData.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( u'\u2248', 5270, HydrusData.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( u'\u2248', 0, HydrusData.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 5270, HydrusData.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 5269, HydrusData.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HydrusData.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HydrusData.ConvertUnitToInteger( 'KB' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HydrusData.ConvertUnitToInteger( 'MB' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HydrusData.ConvertUnitToInteger( 'GB' ) ), 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '<', 201 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '<', 200 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( u'\u2248', 200 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( u'\u2248', 60 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( u'\u2248', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '=', 200 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '=', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '>', 200 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_WIDTH, ( '>', 199 ), 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LIMIT, 100, 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LIMIT, 1, 1 ) )
        # limit is not applied in file_query_ids! we do it later!
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LIMIT, 0, 1 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        service_keys_to_content_updates = {}
        
        service_keys_to_content_updates[ CC.LOCAL_FILE_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( hash, ) ), )
        service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = ( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ), )
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None, 1 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 2 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 1 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '<', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 0 ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '=', 1 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '>', 0 ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, ( '>', 1 ), 0 ) )
        
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
        
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
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
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ) )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_LOCAL, None, 0 ) )
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_NOT_LOCAL, None, 0 ) )
        
        run_system_predicate_tests( tests )
        
    
    def test_file_system_predicates( self ):
        
        self._clear_db()
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        self._write( 'import_file', path )
        
        #
        
        result = self._read( 'file_system_predicates', CC.LOCAL_FILE_SERVICE_KEY )
        
        predicates = []
        
        predicates.append( HydrusData.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None ), counts = { HC.CURRENT : 1 } ) )
        predicates.append( HydrusData.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None ), counts = { HC.CURRENT : 1 } ) )
        predicates.append( HydrusData.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None ), counts = { HC.CURRENT : 0 } ) )
        predicates.extend( [ HydrusData.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( system_predicate_type, None ) ) for system_predicate_type in [ HC.SYSTEM_PREDICATE_TYPE_UNTAGGED, HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_LIMIT, HC.SYSTEM_PREDICATE_TYPE_SIZE, HC.SYSTEM_PREDICATE_TYPE_AGE, HC.SYSTEM_PREDICATE_TYPE_HASH, HC.SYSTEM_PREDICATE_TYPE_WIDTH, HC.SYSTEM_PREDICATE_TYPE_HEIGHT, HC.SYSTEM_PREDICATE_TYPE_RATIO, HC.SYSTEM_PREDICATE_TYPE_DURATION, HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, HC.SYSTEM_PREDICATE_TYPE_MIME, HC.SYSTEM_PREDICATE_TYPE_RATING, HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE ] ] )
        
        self.assertEqual( result, predicates )
        
        for i in range( len( predicates ) ): self.assertEqual( result[i].GetCount(), predicates[i].GetCount() )
        
    
    def test_gui_sessions( self ):
        
        info = []
        
        info.append( ( 'blank', 'class_text', ( CC.LOCAL_FILE_SERVICE_KEY, ), { 'initial_hashes' : [], 'initial_media_results' : [], 'initial_predicates' : [] } ) )
        info.append( ( 'system', 'class_text', ( CC.LOCAL_FILE_SERVICE_KEY, ), { 'initial_hashes' : [ os.urandom( 32 ) for i in range( 8 ) ], 'initial_media_results' : [], 'initial_predicates' : [ ClientSearch.SYSTEM_PREDICATE_ARCHIVE ] } ) )
        info.append( ( 'tags', 'class_text', ( CC.LOCAL_FILE_SERVICE_KEY, ), { 'initial_hashes' : [ os.urandom( 32 ) for i in range( 4 ) ], 'initial_media_results' : [], 'initial_predicates' : [ HydrusData.Predicate( HC.PREDICATE_TYPE_TAG, 'tag', counts = { HC.CURRENT : 1, HC.PENDING : 3 } ) ] } ) )
        
        self._write( 'gui_session', 'normal', info )
        
        result = self._read( 'gui_sessions' )
        
        self.assertEqual( result, { 'normal' : info } )
        
    
    def test_imageboard( self ):
        
        [ ( site_name_4chan, read_imageboards ) ] = self._read( 'imageboards' ).items()
        
        self.assertEqual( site_name_4chan, '4chan' )
        
        [ ( site_name_4chan, imageboards ) ] = ClientDefaults.GetDefaultImageboards()
        
        read_imageboards = { imageboard.GetName() : imageboard for imageboard in read_imageboards }
        imageboards = { imageboard.GetName() : imageboard for imageboard in imageboards }
        
        self.assertItemsEqual( imageboards, read_imageboards )
        
    
    def test_import( self ):
        
        self._clear_db()
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        generate_media_result = True
        
        ( written_result, written_hash ) = self._write( 'import_file', path )
        
        self.assertEqual( written_result, 'successful' )
        self.assertEqual( written_hash, hash )
        
        ( written_result, written_media_result ) = self._write( 'import_file', path, generate_media_result = True )
        
        self.assertEqual( written_result, 'redundant' )
        
        ( mr_hash, mr_inbox, mr_size, mr_mime, mr_timestamp, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words, mr_tags_manager, mr_locations_manager, mr_local_ratings, mr_remote_ratings ) = written_media_result.ToTuple()
        
        now = HydrusData.GetNow()
        
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_inbox, True )
        self.assertEqual( mr_size, 5270 )
        self.assertEqual( mr_mime, HC.IMAGE_PNG )
        self.assertEqual( mr_hash, hash )
        self.assertLessEqual( now - 10, mr_timestamp )
        self.assertLessEqual( mr_timestamp, now + 10 )
        self.assertEqual( mr_width, 200 )
        self.assertEqual( mr_height, 200 )
        self.assertEqual( mr_duration, None )
        self.assertEqual( mr_num_frames, None )
        self.assertEqual( mr_num_words, None )
        
    
    def test_import_folders( self ):
        
        path1 = 'path1'
        path2 = 'path2'
        
        details1 = { 'details' : 1 }
        details2 = { 'details' : 2 }
        details3 = { 'details' : 3 }
        
        #
        
        result = self._read( 'import_folders' )
        
        self.assertEqual( result, {} )
        
        #
        
        self._write( 'import_folder', path1, details1 )
        self._write( 'import_folder', path2, details2 )
        
        result = self._read( 'import_folders' )
        
        self.assertItemsEqual( { path1 : details1, path2 : details2 }, result )
        
        #
        
        self._write( 'delete_import_folder', path1 )
        
        result = self._read( 'import_folders' )
        
        self.assertItemsEqual( { path2 : details2 }, result )
        
        #
        
        self._write( 'import_folder', path2, details3 )
        
        #
        
        result = self._read( 'import_folders' )
        
        self.assertItemsEqual( { path2 : details3 }, result )
        
    
    def test_init( self ):
        
        self.assertTrue( os.path.exists( HC.DB_DIR ) )
        
        self.assertTrue( os.path.exists( HC.DB_DIR + os.path.sep + 'client.db' ) )
        
        self.assertTrue( os.path.exists( HC.CLIENT_FILES_DIR ) )
        
        self.assertTrue( os.path.exists( HC.CLIENT_THUMBNAILS_DIR ) )
    
        hex_chars = '0123456789abcdef'
        
        for ( one, two ) in itertools.product( hex_chars, hex_chars ):
            
            dir = HC.CLIENT_FILES_DIR + os.path.sep + one + two
            
            self.assertTrue( os.path.exists( dir ) )
            
            dir = HC.CLIENT_THUMBNAILS_DIR + os.path.sep + one + two
            
            self.assertTrue( os.path.exists( dir ) )
            
        
    
    def test_md5_status( self ):
        
        self._clear_db()
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = 'fdadb2cae78f2dfeb629449cd005f2a2'.decode( 'hex' )
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        #
        
        result = self._read( 'md5_status', md5 )
        
        self.assertEqual( result, ( 'new', None ) )
        
        #
        
        self._write( 'import_file', path )
        
        #
        
        result = self._read( 'md5_status', md5 )
        
        self.assertEqual( result, ( 'redundant', hash ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ) )
        
        service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : ( content_update, ) }
        
        self._write( 'content_updates', service_keys_to_content_updates )
        
        #
        
        HC.options[ 'exclude_deleted_files' ] = True
        
        result = self._read( 'md5_status', md5 )
        
        self.assertEqual( result, ( 'deleted', None ) )
        
        HC.options[ 'exclude_deleted_files' ] = False
        
        result = self._read( 'md5_status', md5 )
        
        self.assertEqual( result, ( 'new', None ) )
        
    
    def test_media_results( self ):
        
        self._clear_db()
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = 'fdadb2cae78f2dfeb629449cd005f2a2'.decode( 'hex' )
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        self._write( 'import_file', path )
        
        #
        
        ( media_result, ) = self._read( 'media_results', CC.LOCAL_FILE_SERVICE_KEY, ( hash, ) )
        
        ( mr_hash, mr_inbox, mr_size, mr_mime, mr_timestamp, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words, mr_tags_manager, mr_locations_manager, mr_local_ratings, mr_remote_ratings ) = media_result.ToTuple()
        
        now = HydrusData.GetNow()
        
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_inbox, True )
        self.assertEqual( mr_size, 5270 )
        self.assertEqual( mr_mime, HC.IMAGE_PNG )
        self.assertEqual( mr_hash, hash )
        self.assertLessEqual( now - 10, mr_timestamp )
        self.assertLessEqual( mr_timestamp, now + 10 )
        self.assertEqual( mr_width, 200 )
        self.assertEqual( mr_height, 200 )
        self.assertEqual( mr_duration, None )
        self.assertEqual( mr_num_frames, None )
        self.assertEqual( mr_num_words, None )
        
        ( media_result, ) = self._read( 'media_results_from_ids', CC.LOCAL_FILE_SERVICE_KEY, ( 1, ) )
        
        ( mr_hash, mr_inbox, mr_size, mr_mime, mr_timestamp, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words, mr_tags_manager, mr_locations_manager, mr_local_ratings, mr_remote_ratings ) = media_result.ToTuple()
        
        now = HydrusData.GetNow()
        
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_inbox, True )
        self.assertEqual( mr_size, 5270 )
        self.assertEqual( mr_mime, HC.IMAGE_PNG )
        self.assertEqual( mr_hash, hash )
        self.assertLessEqual( now - 10, mr_timestamp )
        self.assertLessEqual( mr_timestamp, now + 10 )
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
        
        self.assertItemsEqual( result, info )
        
        result = self._read( 'tag_censorship', CC.LOCAL_TAG_SERVICE_KEY )
        
        self.assertEqual( result, ( False, [ ':', 'series:' ] ) )
        
    
    def test_news( self ):
        
        result = self._read( 'news', CC.LOCAL_TAG_SERVICE_KEY )
        
        self.assertEqual( result, [] )
        
        #
        
        news = []
        
        news.append( ( 'hello', HydrusData.GetNow() - 30000 ) )
        news.append( ( 'hello again', HydrusData.GetNow() - 20000 ) )
        
        service_updates = dict()
        
        service_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ServiceUpdate( HC.SERVICE_UPDATE_NEWS, news ) ]
        
        self._write( 'service_updates', service_updates )
        
        #
        
        result = self._read( 'news', CC.LOCAL_TAG_SERVICE_KEY )
        
        self.assertItemsEqual( result, news )
        
    
    def test_nums_pending( self ):
        
        result = self._read( 'nums_pending' )
        
        self.assertEqual( result, {} )
        
        # we can do more testing when I add repo service to this testing framework
        
    
    def test_pending( self ):
        
        pass
        
        # result = self._read( 'pending', service_key )
        # do more when I do remote repos
        
    
    def test_pixiv_account( self ):
        
        result = self._read( 'pixiv_account' )
        
        self.assertTrue( result, ( '', '' ) )
        
        pixiv_id = 123456
        password = 'password'
        
        self._write( 'pixiv_account', ( pixiv_id, password ) )
        
        result = self._read( 'pixiv_account' )
        
        self.assertTrue( result, ( pixiv_id, password ) )
        
    
    def test_ratings_filter( self ):
        
        # add ratings servicess
        # fetch no half-ratings
        # then add some half-ratings to files
        # fetch them
        # apply some full ratings
        # fetch them, check the difference
        
        pass
        
    
    def test_ratings_media_result( self ):
        
        # add some ratings, slice different media results?
        # check exactly what this does again, figure a good test
        
        pass
        
    
    def test_services( self ):
        
        result = self._read( 'services', ( HC.LOCAL_FILE, HC.LOCAL_TAG ) )
        
        result_service_keys = { service.GetServiceKey() for service in result }
        
        self.assertItemsEqual( { CC.LOCAL_FILE_SERVICE_KEY, CC.LOCAL_TAG_SERVICE_KEY }, result_service_keys )
        
        #
        
        result = self._read( 'service_info', CC.LOCAL_FILE_SERVICE_KEY )
        
        self.assertEqual( type( result ), dict )
        
        for ( k, v ) in result.items():
            
            self.assertEqual( type( k ), int )
            self.assertEqual( type( v ), int )
            
        
        #
        
        def test_written_services( written_services, service_tuples ):
            
            self.assertEqual( len( written_services ), len( service_tuples ) )
            
            keys_to_service_tuples = { service_key : ( service_type, name, info ) for ( service_key, service_type, name, info ) in service_tuples }
            
            for service in written_services:
                
                service_key = service.GetServiceKey()
                
                self.assertIn( service_key, keys_to_service_tuples )
                
                ( service_type, name, info ) = keys_to_service_tuples[ service_key ]
                
                self.assertEqual( service_type, service.GetServiceType() )
                self.assertEqual( name, service.GetName() )
                
                for ( k, v ) in service.GetInfo().items():
                    
                    if k != 'account': self.assertEqual( v, info[ k ] )
                    
                
            
        
        info = {}
        
        info[ 'host' ] = 'example_host'
        info[ 'port' ] = 80
        info[ 'access_key' ] = os.urandom( 32 ) 
        
        new_tag_repo = ( os.urandom( 32 ), HC.TAG_REPOSITORY, 'new tag repo', info )
        
        info = {}
        
        info[ 'host' ] = 'example_host2'
        info[ 'port' ] = 80
        info[ 'access_key' ] = os.urandom( 32 )
        
        other_new_tag_repo = ( os.urandom( 32 ), HC.TAG_REPOSITORY, 'new tag repo2', info )
        
        info = {}
        
        info[ 'like' ] = 'love'
        info[ 'dislike' ] = 'hate'
        
        new_local_like = ( os.urandom( 32 ), HC.LOCAL_RATING_LIKE, 'new local rating', info )
        
        info = {}
        
        info[ 'lower' ] = 1
        info[ 'upper' ] = 5
        
        new_local_numerical = ( os.urandom( 32 ), HC.LOCAL_RATING_NUMERICAL, 'new local numerical', info )
        
        edit_log = []
        
        edit_log.append( HydrusData.EditLogActionAdd( new_tag_repo ) )
        edit_log.append( HydrusData.EditLogActionAdd( other_new_tag_repo ) )
        edit_log.append( HydrusData.EditLogActionAdd( new_local_like ) )
        edit_log.append( HydrusData.EditLogActionAdd( new_local_numerical ) )
        
        self._write( 'update_services', edit_log )
        
        written_services = set( self._read( 'services', ( HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ) )
        
        test_written_services( written_services, ( new_tag_repo, other_new_tag_repo, new_local_like, new_local_numerical ) )
        
        #
        
        ( service_key, service_type, name, info ) = other_new_tag_repo
        
        name = 'a better name'
        
        info = dict( info )
        
        info[ 'host' ] = 'corrected host'
        info[ 'port' ] = 85
        info[ 'access_key' ] = os.urandom( 32 )
        
        other_new_tag_repo_updated = ( service_key, service_type, name, info )
        
        edit_log = []
        
        edit_log.append( HydrusData.EditLogActionDelete( new_local_like[0] ) )
        edit_log.append( HydrusData.EditLogActionEdit( other_new_tag_repo_updated[0], other_new_tag_repo_updated ) )
        
        self._write( 'update_services', edit_log )
        
        written_services = set( self._read( 'services', ( HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ) )
        
        test_written_services( written_services, ( new_tag_repo, other_new_tag_repo_updated, new_local_numerical ) )
        
        #
        
        edit_log = []
        
        edit_log.append( HydrusData.EditLogActionDelete( other_new_tag_repo_updated[0] ) )
        
        self._write( 'update_services', edit_log )
        
        written_services = set( self._read( 'services', ( HC.TAG_REPOSITORY, HC.LOCAL_RATING_LIKE, HC.LOCAL_RATING_NUMERICAL ) ) )
        
        test_written_services( written_services, ( new_tag_repo, new_local_numerical ) )
        
    
    def test_sessions( self ):
        
        result = self._read( 'hydrus_sessions' )
        
        self.assertEqual( result, [] )
        
        session = ( CC.LOCAL_FILE_SERVICE_KEY, os.urandom( 32 ), HydrusData.GetNow() + 100000 )
        
        self._write( 'hydrus_session', *session )
        
        result = self._read( 'hydrus_sessions' )
        
        self.assertEqual( result, [ session ] )
        
        #
        
        result = self._read( 'web_sessions' )
        
        self.assertEqual( result, [] )
        
        session = ( 'website name', [ 'cookie 1', 'cookie 2' ], HydrusData.GetNow() + 100000 )
        
        self._write( 'web_session', *session )
        
        result = self._read( 'web_sessions' )
        
        self.assertEqual( result, [ session ] )
        
    
    def test_shutdown_timestamps( self ):
        
        result = self._read( 'shutdown_timestamps' )
        
        self.assertEqual( type( result ), collections.defaultdict )
        
        for ( k, v ) in result.items():
            
            self.assertEqual( type( k ), int )
            self.assertEqual( type( v ), int )
            
        

class TestServerDB( unittest.TestCase ):
    
    def _read( self, action, *args, **kwargs ): return self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return self._db.Write( action, HC.HIGH_PRIORITY, *args, **kwargs )
    
    @classmethod
    def setUpClass( self ):
        
        self._old_db_dir = HC.DB_DIR
        self._old_server_files_dir = HC.SERVER_FILES_DIR
        self._old_server_thumbnails_dir = HC.SERVER_THUMBNAILS_DIR
        
        HC.DB_DIR = tempfile.mkdtemp()
        
        HC.SERVER_FILES_DIR = HC.DB_DIR + os.path.sep + 'server_files'
        HC.SERVER_THUMBNAILS_DIR = HC.DB_DIR + os.path.sep + 'server_thumbnails'
        
        if not os.path.exists( HC.DB_DIR ): os.mkdir( HC.DB_DIR )
        
        self._db = ServerDB.DB()
        
        threading.Thread( target = self._db.MainLoop, name = 'Database Main Loop' ).start()
        
    
    @classmethod
    def tearDownClass( self ):
        
        self._db.Shutdown()
        
        while not self._db.LoopIsFinished(): time.sleep( 0.1 )
        
        def make_temp_files_deletable( function_called, path, traceback_gumpf ):
            
            os.chmod( path, stat.S_IWRITE )
            
            try: function_called( path ) # try again
            except: pass
            
        
        if os.path.exists( HC.DB_DIR ): shutil.rmtree( HC.DB_DIR, onerror = make_temp_files_deletable )
        
        HC.DB_DIR = self._old_db_dir
        HC.SERVER_FILES_DIR = self._old_server_files_dir
        HC.SERVER_THUMBNAILS_DIR = self._old_server_thumbnails_dir
        
    
    def _test_account_creation( self ):
        
        result = self._read( 'account_types', self._tag_service_key )
        
        ( service_admin_at, ) = result
        
        self.assertEqual( service_admin_at.GetTitle(), 'service admin' )
        self.assertEqual( service_admin_at.GetPermissions(), [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN ] )
        self.assertEqual( service_admin_at.GetMaxBytes(), None )
        self.assertEqual( service_admin_at.GetMaxRequests(), None )
        
        #
        
        user_at = HydrusData.AccountType( 'user', [ HC.GET_DATA, HC.POST_DATA ], ( 50000, 500 ) )
        
        edit_log = [ ( HC.ADD, user_at ) ]
        
        self._write( 'account_types', self._tag_service_key, edit_log )
        
        result = self._read( 'account_types', self._tag_service_key )
        
        ( at_1, at_2 ) = result
        
        d = { at_1.GetTitle() : at_1, at_2.GetTitle() : at_2 }
        
        at = d[ 'user' ]
        
        self.assertEqual( at.GetPermissions(), [ HC.GET_DATA, HC.POST_DATA ] )
        self.assertEqual( at.GetMaxBytes(), 50000 )
        self.assertEqual( at.GetMaxRequests(), 500 )
        
        #
        
        user_at_diff = HydrusData.AccountType( 'user different', [ HC.GET_DATA ], ( 40000, None ) )
        
        edit_log = [ ( HC.EDIT, ( 'user', user_at_diff ) ) ]
        
        self._write( 'account_types', self._tag_service_key, edit_log )
        
        result = self._read( 'account_types', self._tag_service_key )
        
        ( at_1, at_2 ) = result
        
        d = { at_1.GetTitle() : at_1, at_2.GetTitle() : at_2 }
        
        at = d[ 'user different' ]
        
        self.assertEqual( at.GetPermissions(), [ HC.GET_DATA ] )
        self.assertEqual( at.GetMaxBytes(), 40000 )
        self.assertEqual( at.GetMaxRequests(), None )
        
        #
        
        r_keys = self._read( 'registration_keys', self._tag_service_key, 5, 'user different', 86400 * 365 )
        
        self.assertEqual( len( r_keys ), 5 )
        
        for r_key in r_keys: self.assertEqual( len( r_key ), 32 )
        
        r_key = r_keys[0]
        
        access_key = self._read( 'access_key', r_key )
        access_key_2 = self._read( 'access_key', r_key )
        
        self.assertNotEqual( access_key, access_key_2 )
        
        self.assertRaises( HydrusExceptions.ForbiddenException, self._read, 'account_key_from_access_key', self._tag_service_key, access_key )
        
        account_key = self._read( 'account_key_from_access_key', self._tag_service_key, access_key_2 )
        
        self.assertRaises( HydrusExceptions.ForbiddenException, self._read, 'access_key', r_key )
        
    
    def _test_content_creation( self ):
        
        # create some tag and hashes business, try uploading a file, and test that
        
        # fetch content update, test it. I think that works
        
        pass
        
    
    def _test_init_server_admin( self ):
        
        result = self._read( 'init' ) # an access key
        
        self.assertEqual( type( result ), str )
        self.assertEqual( len( result ), 32 )
        
        self._admin_access_key = result
        
        result = self._read( 'account_key_from_access_key', HC.SERVER_ADMIN_KEY, self._admin_access_key )
        
        self.assertEqual( type( result ), str )
        self.assertEqual( len( result ), 32 )
        
        self._admin_account_key = result
        
    
    def _test_service_creation( self ):
        
        self._tag_service_key = os.urandom( 32 )
        self._file_service_key = os.urandom( 32 )
        
        edit_log = []
        
        t_options = { 'max_monthly_data' : None, 'message' : 'tag repo message', 'port' : 100, 'upnp' : None }
        f_options = { 'max_monthly_data' : None, 'message' : 'file repo message', 'port' : 101, 'upnp' : None }
        
        edit_log.append( ( HC.ADD, ( self._tag_service_key, HC.TAG_REPOSITORY, t_options ) ) )
        edit_log.append( ( HC.ADD, ( self._file_service_key, HC.FILE_REPOSITORY, f_options ) ) )
        
        result = self._write( 'services', self._admin_account_key, edit_log )
        
        self.assertIn( self._tag_service_key, result )
        
        self._tag_service_admin_access_key = result[ self._tag_service_key ]
        
        self.assertEqual( type( self._tag_service_admin_access_key ), str )
        self.assertEqual( len( self._tag_service_admin_access_key ), 32 )
        
        self.assertIn( self._file_service_key, result )
        
        self._file_service_admin_access_key = result[ self._file_service_key ]
        
        self.assertEqual( type( self._tag_service_admin_access_key ), str )
        self.assertEqual( len( self._tag_service_admin_access_key ), 32 )
        
        #
        
        result = self._read( 'service_keys', HC.REPOSITORIES )
        
        self.assertEqual( set( result ), { self._tag_service_key, self._file_service_key } )
        
        #
        
        result = self._read( 'services_info' )
        
        services_info = { service_key : ( service_type, options ) for ( service_key, service_type, options ) in result }
        
        self.assertEqual( services_info[ HC.SERVER_ADMIN_KEY ], ( 99, { 'max_monthly_data' : None, 'message' : 'hydrus server administration service', 'max_storage' : None, 'upnp' : None, 'port' : 45870 } ) )
        self.assertEqual( services_info[ self._tag_service_key ], ( HC.TAG_REPOSITORY, t_options ) )
        self.assertEqual( services_info[ self._file_service_key ], ( HC.FILE_REPOSITORY, f_options ) )
        
        #
        
        f_options_modified = dict( f_options )
        f_options_modified[ 'port' ] = 102
        
        edit_log = [ ( HC.EDIT, ( self._file_service_key, HC.FILE_REPOSITORY, f_options_modified ) ) ]
        
        self._write( 'services', self._admin_account_key, edit_log )
        
        result = self._read( 'services_info' )
        
        services_info = { service_key : ( service_type, options ) for ( service_key, service_type, options ) in result }
        
        self.assertEqual( services_info[ self._file_service_key ], ( HC.FILE_REPOSITORY, f_options_modified ) )
        
    
    def test_server( self ):
        
        self._test_init_server_admin()
        
        self._test_service_creation()
        
        self._test_account_creation()
        
        self._test_content_creation()
        
