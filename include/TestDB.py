import ClientConstants as CC
import ClientDB
import collections
import HydrusConstants as HC
import itertools
import os
import shutil
import stat
import TestConstants
import time
import threading
import unittest
import yaml

class TestClientDB( unittest.TestCase ):
    
    def _clear_db( self ):
        
        ( db, c ) = self._db._GetDBCursor()
        
        c.execute( 'DELETE FROM files_info;' )
        c.execute( 'DELETE FROM mappings;' )
        
    
    def _read( self, action, *args, **kwargs ): return self._db.Read( action, HC.HIGH_PRIORITY, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return self._db.Write( action, HC.HIGH_PRIORITY, True, *args, **kwargs )
    
    @classmethod
    def setUpClass( self ):
        
        self._old_db_dir = HC.DB_DIR
        self._old_client_files_dir = HC.CLIENT_FILES_DIR
        self._old_client_thumbnails_dir = HC.CLIENT_THUMBNAILS_DIR
        
        HC.DB_DIR = HC.TEMP_DIR + os.path.sep + os.urandom( 32 ).encode( 'hex' )
        
        HC.CLIENT_FILES_DIR = HC.DB_DIR + os.path.sep + 'client_files'
        HC.CLIENT_THUMBNAILS_DIR = HC.DB_DIR + os.path.sep + 'client_thumbnails'
        
        if not os.path.exists( HC.TEMP_DIR ): os.mkdir( HC.TEMP_DIR )
        if not os.path.exists( HC.DB_DIR ): os.mkdir( HC.DB_DIR )
        
        self._db = ClientDB.DB()
        
        threading.Thread( target = self._db.MainLoop, name = 'Database Main Loop' ).start()
        
    
    @classmethod
    def tearDownClass( self ):
        
        self._db.Shutdown()
        
        while not self._db.GetLoopFinished(): time.sleep( 0.1 )
        
        def make_temp_files_deletable( function_called, path, traceback_gumpf ):
            
            os.chmod( path, stat.S_IWRITE )
            
            function_called( path ) # try again
            
        
        if os.path.exists( HC.DB_DIR ): shutil.rmtree( HC.DB_DIR, onerror = make_temp_files_deletable )
        
        HC.DB_DIR = self._old_db_dir
        HC.CLIENT_FILES_DIR = self._old_client_files_dir
        HC.CLIENT_THUMBNAILS_DIR = self._old_client_thumbnails_dir
        
    
    def test_4chan_pass( self ):
        
        result = self._read( '4chan_pass' )
        
        self.assertTrue( result, ( '', '', 0 ) )
        
        token = 'token'
        pin = 'pin'
        timeout = HC.GetNow() + 100000
        
        self._write( '4chan_pass', token, pin, timeout )
        
        result = self._read( '4chan_pass' )
        
        self.assertTrue( result, ( token, pin, timeout ) )
        
    
    def test_autocomplete( self ):
        
        self._clear_db()
        
        result = self._read( 'autocomplete_tags', half_complete_tag = 'c' )
        
        self.assertEqual( result.GetMatches( 'c' ), [] )
        
        result = self._read( 'autocomplete_tags', half_complete_tag = 'series:' )
        
        self.assertEqual( result.GetMatches( 'series:' ), [] )
        
        #
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        self._write( 'import_file', path )
        
        #
        
        service_identifiers_to_content_updates = {}
        
        content_updates = []

        content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ) )
        content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
        service_identifiers_to_content_updates[ HC.LOCAL_TAG_SERVICE_IDENTIFIER ] = content_updates
        
        self._write( 'content_updates', service_identifiers_to_content_updates )
        
        # cars
        
        result = self._read( 'autocomplete_tags', half_complete_tag = 'c' )
        
        preds = set()
        
        preds.add( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'cars' ), 1 ) )
        preds.add( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'car' ), 1 ) )
        preds.add( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'series:cars' ), 1 ) )
        
        read_preds = result.GetMatches( 'c' )
        
        # count isn't tested in predicate.__eq__, I think
        
        for p in read_preds: self.assertEqual( p.GetCount(), 1 )
        
        self.assertEqual( set( read_preds ), preds )
        
        #
        
        result = self._read( 'autocomplete_tags', half_complete_tag = 'ser' )
        
        read_preds = result.GetMatches( 'ser' )
        
        self.assertEqual( read_preds, [] )
        
        #
        
        result = self._read( 'autocomplete_tags', half_complete_tag = 'series:c' )
        
        pred = HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'series:cars' ), 1 )
        
        ( read_pred, ) = result.GetMatches( 'series:c' )
        
        self.assertEqual( read_pred.GetCount(), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_tags', tag = 'car' )
        
        pred = HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'car' ), 1 )
        
        ( read_pred, ) = result.GetMatches( 'car' )
        
        self.assertEqual( read_pred.GetCount(), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_tags', tag = 'c' )
        
        read_preds = result.GetMatches( 'c' )
        
        self.assertEqual( read_preds, [] )
        
    
    def test_booru( self ):
        
        for ( name, booru ) in CC.DEFAULT_BOORUS.items():
            
            read_booru = self._read( 'booru', name )
            
            self.assertEqual( booru.GetData(), read_booru.GetData() )
            
        
        #
        
        result = self._read( 'boorus' )
        
        read_boorus = { booru.GetName() : booru for booru in result }
        
        for name in CC.DEFAULT_BOORUS: self.assertEqual( read_boorus[ name ].GetData(), CC.DEFAULT_BOORUS[ name ].GetData() )
        
        #
    
        name = 'blah'
        search_url = 'url'
        search_separator = '%20'
        advance_by_page_num = True
        thumb_classname = 'thumb'
        image_id = None
        image_data = 'Download'
        tag_classnames_to_namespaces = { 'tag' : '' }
        
        booru = CC.Booru( name, search_url, search_separator, advance_by_page_num, thumb_classname, image_id, image_data, tag_classnames_to_namespaces )
        
        edit_log = [ ( HC.ADD, 'blah' ), ( HC.EDIT, ( 'blah', booru ) ) ]
        
        self._write( 'update_boorus', edit_log )
        
        read_booru = self._read( 'booru', name )
        
        self.assertEqual( booru.GetData(), read_booru.GetData() )
        
        #
        
        edit_log = [ ( HC.DELETE, 'blah' ) ]
        
        self._write( 'update_boorus', edit_log )
        
        with self.assertRaises( Exception ):
            
            read_booru = self._read( 'booru', name )
            
        
    
    def test_downloads( self ):
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, set() )
        
        #
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        service_identifiers_to_content_updates = {}
        
        service_identifiers_to_content_updates[ HC.LOCAL_FILE_SERVICE_IDENTIFIER ] = ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_PENDING, ( hash, ) ), )
        
        self._write( 'content_updates', service_identifiers_to_content_updates )
        
        #
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, { hash } )
        
        #
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        service_identifiers_to_content_updates = {}
        
        service_identifiers_to_content_updates[ HC.LOCAL_FILE_SERVICE_IDENTIFIER ] = ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_RESCIND_PENDING, ( hash, ) ), )
        
        self._write( 'content_updates', service_identifiers_to_content_updates )
        
        #
        
        result = self._read( 'downloads' )
        
        self.assertEqual( result, set() )
        
    
    def test_favourite_custom_filter_actions( self ):
        
        result = self._read( 'favourite_custom_filter_actions' )
        
        self.assertEqual( result, dict() )
        
        #
        
        favourite_custom_filter_actions = { 'a' : 'blah', 'b' : 'bleh' }
        
        self._write( 'favourite_custom_filter_actions', favourite_custom_filter_actions )
        
        #
        
        result = self._read( 'favourite_custom_filter_actions' )
        
        self.assertEqual( result, favourite_custom_filter_actions )
        
    
    def test_file_query_ids( self ):
        
        self._clear_db()
        
        def run_namespace_predicate_tests( tests ):
            
            for ( operator, namespace, result ) in tests:
                
                predicates = [ HC.Predicate( HC.PREDICATE_TYPE_NAMESPACE, ( operator, namespace ), None ) ]
                
                search_context = CC.FileSearchContext( file_service_identifier = HC.LOCAL_FILE_SERVICE_IDENTIFIER, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_system_predicate_tests( tests ):
            
            for ( predicate_type, info, result ) in tests:
                
                predicates = [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( predicate_type, info ), None ) ]
                
                search_context = CC.FileSearchContext( file_service_identifier = HC.LOCAL_FILE_SERVICE_IDENTIFIER, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_tag_predicate_tests( tests ):
            
            for ( operator, tag, result ) in tests:
                
                predicates = [ HC.Predicate( HC.PREDICATE_TYPE_TAG, ( operator, tag ), None ) ]
                
                search_context = CC.FileSearchContext( file_service_identifier = HC.LOCAL_FILE_SERVICE_IDENTIFIER, predicates = predicates )
                
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
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( False, HC.CURRENT, HC.LOCAL_FILE_SERVICE_IDENTIFIER ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( False, HC.PENDING, HC.LOCAL_FILE_SERVICE_IDENTIFIER ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( True, HC.CURRENT, HC.LOCAL_FILE_SERVICE_IDENTIFIER ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE, ( True, HC.PENDING, HC.LOCAL_FILE_SERVICE_IDENTIFIER ), 0 ) )
        
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
        
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 0, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 5270, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '<', 5271, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '=', 5270, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '=', 0, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( u'\u2248', 5270, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( u'\u2248', 0, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 5270, HC.ConvertUnitToInteger( 'B' ) ), 0 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 5269, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HC.ConvertUnitToInteger( 'B' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HC.ConvertUnitToInteger( 'KB' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HC.ConvertUnitToInteger( 'MB' ) ), 1 ) )
        tests.append( ( HC.SYSTEM_PREDICATE_TYPE_SIZE, ( '>', 0, HC.ConvertUnitToInteger( 'GB' ) ), 1 ) )
        
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
        
        service_identifiers_to_content_updates = {}
        
        service_identifiers_to_content_updates[ HC.LOCAL_FILE_SERVICE_IDENTIFIER ] = ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( hash, ) ), )
        service_identifiers_to_content_updates[ HC.LOCAL_TAG_SERVICE_IDENTIFIER ] = ( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ), )
        
        self._write( 'content_updates', service_identifiers_to_content_updates )
        
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
        
        tests.append( ( '+', 'car', 1 ) )
        tests.append( ( '-', 'car', 0 ) )
        tests.append( ( '+', 'bus', 0 ) )
        tests.append( ( '-', 'bus', 1 ) )
        
        run_tag_predicate_tests( tests )
        
        #
        
        tests = []
        
        tests.append( ( '+', 'series', 0 ) )
        tests.append( ( '-', 'series', 1 ) )
        
        run_namespace_predicate_tests( tests )
        
        #
        
        service_identifiers_to_content_updates = {}
        
        content_updates = []
        
        content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
        service_identifiers_to_content_updates[ HC.LOCAL_TAG_SERVICE_IDENTIFIER ] = content_updates
        
        self._write( 'content_updates', service_identifiers_to_content_updates )
        
        #
        
        tests = []
        
        tests.append( ( '+', 'maker:ford', 1 ) )
        tests.append( ( '+', 'ford', 1 ) )
        
        run_tag_predicate_tests( tests )
        
        #
        
        tests = []
        
        tests.append( ( '+', 'series', 1 ) )
        tests.append( ( '-', 'series', 0 ) )
        
        run_namespace_predicate_tests( tests )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ) )
        
        service_identifiers_to_content_updates = { HC.LOCAL_FILE_SERVICE_IDENTIFIER : ( content_update, ) }
        
        self._write( 'content_updates', service_identifiers_to_content_updates )
        
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
        
        result = self._read( 'file_system_predicates', HC.LOCAL_FILE_SERVICE_IDENTIFIER )
        
        predicates = []
        
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_EVERYTHING, None ), 1 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_INBOX, None ), 1 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( HC.SYSTEM_PREDICATE_TYPE_ARCHIVE, None ), 0 ) )
        predicates.extend( [ HC.Predicate( HC.PREDICATE_TYPE_SYSTEM, ( system_predicate_type, None ), None ) for system_predicate_type in [ HC.SYSTEM_PREDICATE_TYPE_UNTAGGED, HC.SYSTEM_PREDICATE_TYPE_NUM_TAGS, HC.SYSTEM_PREDICATE_TYPE_LIMIT, HC.SYSTEM_PREDICATE_TYPE_SIZE, HC.SYSTEM_PREDICATE_TYPE_AGE, HC.SYSTEM_PREDICATE_TYPE_HASH, HC.SYSTEM_PREDICATE_TYPE_WIDTH, HC.SYSTEM_PREDICATE_TYPE_HEIGHT, HC.SYSTEM_PREDICATE_TYPE_RATIO, HC.SYSTEM_PREDICATE_TYPE_DURATION, HC.SYSTEM_PREDICATE_TYPE_NUM_WORDS, HC.SYSTEM_PREDICATE_TYPE_MIME, HC.SYSTEM_PREDICATE_TYPE_RATING, HC.SYSTEM_PREDICATE_TYPE_SIMILAR_TO, HC.SYSTEM_PREDICATE_TYPE_FILE_SERVICE ] ] )
        
        self.assertEqual( result, predicates )
        
        for i in range( len( predicates ) ): self.assertEqual( result[i].GetCount(), predicates[i].GetCount() )
        
    
    def test_imageboard( self ):
        
        [ ( site_name_4chan, read_imageboards ) ] = self._read( 'imageboards' )
        
        self.assertEqual( site_name_4chan, '4chan' )
        
        [ ( site_name_4chan, imageboards ) ] = CC.DEFAULT_IMAGEBOARDS
        
        read_imageboards = { imageboard.GetName() : imageboard for imageboard in read_imageboards }
        imageboards = { imageboard.GetName() : imageboard for imageboard in imageboards }
        
        self.assertItemsEqual( imageboards, read_imageboards )
        
    
    def test_import( self ):
        
        self._clear_db()
        
        hash = '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'
        
        generate_media_result = True
        
        ( written_result, written_hash, written_media_result ) = self._write( 'import_file', path, generate_media_result = True )
        
        self.assertEqual( written_result, 'successful' )
        self.assertEqual( written_hash, hash )
        
        ( mr_hash, mr_inbox, mr_size, mr_mime, mr_timestamp, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words, mr_tags_manager, mr_file_service_identifiers_cdpp, mr_local_ratings, mr_remote_ratings ) = written_media_result.ToTuple()
        
        now = HC.GetNow()
        
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
        
        f1 = ( 'path1', { 'details' : 1 } )
        f2a = ( 'path2', { 'details' : 2 } )
        f2b = ( 'path2', { 'details' : 3 } )
        
        #
        
        result = self._read( 'import_folders' )
        
        self.assertEqual( result, [] )
        
        #
        
        self._write( 'import_folders', [ f1, f2a ] )
        
        #
        
        result = self._read( 'import_folders' )
        
        self.assertItemsEqual( [ f1, f2a ], result )
        
        #
        
        self._write( 'import_folder', *f2b )
        
        #
        
        result = self._read( 'import_folders' )
        
        self.assertItemsEqual( [ f1, f2b ], result )
        
    
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
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ) )
        
        service_identifiers_to_content_updates = { HC.LOCAL_FILE_SERVICE_IDENTIFIER : ( content_update, ) }
        
        self._write( 'content_updates', service_identifiers_to_content_updates )
        
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
        
        ( media_result, ) = self._read( 'media_results', HC.LOCAL_FILE_SERVICE_IDENTIFIER, ( hash, ) )
        
        ( mr_hash, mr_inbox, mr_size, mr_mime, mr_timestamp, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words, mr_tags_manager, mr_file_service_identifiers_cdpp, mr_local_ratings, mr_remote_ratings ) = media_result.ToTuple()
        
        now = HC.GetNow()
        
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
        
        ( media_result, ) = self._read( 'media_results_from_ids', HC.LOCAL_FILE_SERVICE_IDENTIFIER, ( 1, ) )
        
        ( mr_hash, mr_inbox, mr_size, mr_mime, mr_timestamp, mr_width, mr_height, mr_duration, mr_num_frames, mr_num_words, mr_tags_manager, mr_file_service_identifiers_cdpp, mr_local_ratings, mr_remote_ratings ) = media_result.ToTuple()
        
        now = HC.GetNow()
        
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
        
    
    def test_namespace_blacklists( self ):
        
        result = self._read( 'namespace_blacklists' )
        
        self.assertEqual( result, [] )
        
        result = self._read( 'namespace_blacklists', HC.LOCAL_TAG_SERVICE_IDENTIFIER )
        
        self.assertEqual( result, ( True, [] ) )
        
        #
        
        namespace_blacklists = []
        
        namespace_blacklists.append( ( HC.LOCAL_TAG_SERVICE_IDENTIFIER, False, [ '', 'series' ] ) )
        namespace_blacklists.append( ( HC.LOCAL_FILE_SERVICE_IDENTIFIER, True, [ '' ] ) ) # bit dodgy, but whatever!
        
        self._write( 'namespace_blacklists', namespace_blacklists )
        
        #
        
        result = self._read( 'namespace_blacklists' )
        
        self.assertItemsEqual( result, namespace_blacklists )
        
        result = self._read( 'namespace_blacklists', HC.LOCAL_TAG_SERVICE_IDENTIFIER )
        
        self.assertEqual( result, ( False, [ '', 'series' ] ) )
        
    
    def test_news( self ):
        
        result = self._read( 'news', HC.LOCAL_TAG_SERVICE_IDENTIFIER )
        
        self.assertEqual( result, [] )
        
        #
        
        news = []
        
        news.append( ( 'hello', HC.GetNow() - 30000 ) )
        news.append( ( 'hello again', HC.GetNow() - 20000 ) )
        
        service_updates = dict()
        
        service_updates[ HC.LOCAL_TAG_SERVICE_IDENTIFIER ] = [ HC.ServiceUpdate( HC.SERVICE_UPDATE_NEWS, news ) ]
        
        self._write( 'service_updates', service_updates )
        
        #
        
        result = self._read( 'news', HC.LOCAL_TAG_SERVICE_IDENTIFIER )
        
        self.assertItemsEqual( result, news )
        
    
    def test_nums_pending( self ):
        
        result = self._read( 'nums_pending' )
        
        self.assertEqual( result, {} )
        
        # we can do more testing when I add repo service to this testing framework
        
    
    def test_pending( self ):
        
        pass
        
        # result = self._read( 'pending', service_identifier )
        # do more when I do remote repos
        
    
    def test_pixiv_account( self ):
        
        result = self._read( 'pixiv_account' )
        
        self.assertTrue( result, ( '', '' ) )
        
        pixiv_id = 123456
        password = 'password'
        
        self._write( 'pixiv_account', pixiv_id, password )
        
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
        
        result = self._read( 'service_identifiers', ( HC.LOCAL_FILE, ) )
        
        self.assertEqual( result, { HC.LOCAL_FILE_SERVICE_IDENTIFIER } )
        
        result = self._read( 'service_identifiers', ( HC.LOCAL_TAG, ) )
        
        self.assertEqual( result, { HC.LOCAL_TAG_SERVICE_IDENTIFIER } )
        
        result = self._read( 'service_identifiers', ( HC.COMBINED_FILE, ) )
        
        self.assertEqual( result, { HC.COMBINED_FILE_SERVICE_IDENTIFIER } )
        
        result = self._read( 'service_identifiers', ( HC.COMBINED_TAG, ) )
        
        self.assertEqual( result, { HC.COMBINED_TAG_SERVICE_IDENTIFIER } )
        
        result = self._read( 'service_identifiers', ( HC.LOCAL_FILE, HC.COMBINED_FILE ) )
        
        self.assertEqual( result, { HC.LOCAL_FILE_SERVICE_IDENTIFIER, HC.COMBINED_FILE_SERVICE_IDENTIFIER } )
        
        #
        
        result = self._read( 'service', HC.LOCAL_FILE_SERVICE_IDENTIFIER )
        
        self.assertEqual( result.GetServiceIdentifier(), HC.LOCAL_FILE_SERVICE_IDENTIFIER )
        
        result = self._read( 'service', HC.LOCAL_TAG_SERVICE_IDENTIFIER )
        
        self.assertEqual( result.GetServiceIdentifier(), HC.LOCAL_TAG_SERVICE_IDENTIFIER )
        
        result = self._read( 'services', ( HC.LOCAL_FILE, HC.LOCAL_TAG ) )
        
        result_s_is = { service.GetServiceIdentifier() for service in result }
        
        self.assertItemsEqual( { HC.LOCAL_FILE_SERVICE_IDENTIFIER, HC.LOCAL_TAG_SERVICE_IDENTIFIER }, result_s_is )
        
        #
        
        result = self._read( 'service_info', HC.LOCAL_FILE_SERVICE_IDENTIFIER )
        
        self.assertEqual( type( result ), dict )
        
        for ( k, v ) in result.items():
            
            self.assertEqual( type( k ), int )
            self.assertEqual( type( v ), int )
            
        
        #
        
        new_tag_repo = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'new tag repo' )
        new_tag_repo_credentials = CC.Credentials( 'example_host', 80, access_key = os.urandom( 32 ) )
        
        other_new_tag_repo = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'new tag repo2' )
        other_new_tag_repo_credentials = CC.Credentials( 'example_host2', 80, access_key = os.urandom( 32 ) )
        
        new_local_like = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.LOCAL_RATING_LIKE, 'new local rating' )
        new_local_like_extra_info = ( 'love', 'hate' )
        
        new_local_numerical = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.LOCAL_RATING_NUMERICAL, 'new local numerical' )
        new_local_numerical_extra_info = ( 1, 5 )
        
        edit_log = []
        
        edit_log.append( ( HC.ADD, ( new_tag_repo, new_tag_repo_credentials, None ) ) )
        edit_log.append( ( HC.ADD, ( other_new_tag_repo, new_tag_repo_credentials, None ) ) )
        edit_log.append( ( HC.ADD, ( new_local_like, None, new_local_like_extra_info ) ) )
        edit_log.append( ( HC.ADD, ( new_local_numerical, None, new_local_numerical_extra_info ) ) )
        
        self._write( 'update_services', edit_log )
        
        result = self._read( 'service_identifiers', ( HC.TAG_REPOSITORY, ) )
        self.assertEqual( result, { new_tag_repo, other_new_tag_repo } )
        
        result = self._read( 'service_identifiers', ( HC.LOCAL_RATING_LIKE, ) )
        self.assertEqual( result, { new_local_like } )
        
        result = self._read( 'service_identifiers', ( HC.LOCAL_RATING_NUMERICAL, ) )
        self.assertEqual( result, { new_local_numerical } )
        
        #
        
        # should the service key be different or the same?
        other_new_tag_repo_updated = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'a better name' )
        other_new_tag_repo_credentials_updated = CC.Credentials( 'corrected host', 85, access_key = os.urandom( 32 ) )
        
        edit_log = []
        
        edit_log.append( ( HC.DELETE, new_local_like ) )
        edit_log.append( ( HC.EDIT, ( other_new_tag_repo, ( other_new_tag_repo_updated, other_new_tag_repo_credentials_updated, None ) ) ) )
        
        self._write( 'update_services', edit_log )
        
        # now delete local_like, test that
        # edit other_tag_repo, test that
        
        #
        
        result = self._read( 'service', new_tag_repo )
        
        # test credentials
        
        result = self._read( 'services', ( HC.TAG_REPOSITORY, ) )
        
        # test there are two, and test credentials
        
    
    def test_sessions( self ):
        
        result = self._read( 'hydrus_sessions' )
        
        self.assertEqual( result, [] )
        
        session = ( HC.LOCAL_FILE_SERVICE_IDENTIFIER, os.urandom( 32 ), HC.GetNow() + 100000 )
        
        self._write( 'hydrus_session', *session )
        
        result = self._read( 'hydrus_sessions' )
        
        self.assertEqual( result, [ session ] )
        
        #
        
        result = self._read( 'web_sessions' )
        
        self.assertEqual( result, [] )
        
        session = ( 'website name', [ 'cookie 1', 'cookie 2' ], HC.GetNow() + 100000 )
        
        self._write( 'web_session', *session )
        
        result = self._read( 'web_sessions' )
        
        self.assertEqual( result, [ session ] )
        
    
    def test_shutdown_timestamps( self ):
        
        result = self._read( 'shutdown_timestamps' )
        
        self.assertEqual( type( result ), collections.defaultdict )
        
        for ( k, v ) in result.items():
            
            self.assertEqual( type( k ), int )
            self.assertEqual( type( v ), int )
            
        