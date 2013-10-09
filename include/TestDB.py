import ClientConstants as CC
import ClientDB
import HydrusConstants as HC
import itertools
import os
import shutil
import stat
import TestConstants
import time
import threading
import unittest

class TestClientDB( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._old_db_dir = HC.DB_DIR
        self._old_client_files_dir = HC.CLIENT_FILES_DIR
        self._old_client_thumbnails_dir = HC.CLIENT_THUMBNAILS_DIR
        
        HC.DB_DIR = HC.TEMP_DIR + os.path.sep + 'client_db_test'
        
        HC.CLIENT_FILES_DIR = HC.DB_DIR + os.path.sep + 'client_files'
        HC.CLIENT_THUMBNAILS_DIR = HC.DB_DIR + os.path.sep + 'client_thumbnails'
        
        if not os.path.exists( HC.TEMP_DIR ): os.mkdir( HC.TEMP_DIR )
        if not os.path.exists( HC.DB_DIR ): os.mkdir( HC.DB_DIR )
        
        self._db = ClientDB.DB()
        
        threading.Thread( target = self._db.MainLoop, name = 'Database Main Loop' ).start()
        
    
    @classmethod
    def tearDownClass( self ):
        
        self._db.Shutdown()
        
        time.sleep( 2 )
        
        def make_temp_files_deletable( function_called, path, traceback_gumpf ):
            
            os.chmod( path, stat.S_IWRITE )
            
            function_called( path ) # try again
            
        
        if os.path.exists( HC.DB_DIR ): shutil.rmtree( HC.DB_DIR, onerror = make_temp_files_deletable )
        
        HC.DB_DIR = self._old_db_dir
        HC.CLIENT_FILES_DIR = self._old_client_files_dir
        HC.CLIENT_THUMBNAILS_DIR = self._old_client_thumbnails_dir
        
    
    def test_folders_exist( self ):
        
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
            
        
    
    def test_services( self ):
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_FILE, ) )
        self.assertEqual( result, { HC.LOCAL_FILE_SERVICE_IDENTIFIER } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_TAG, ) )
        self.assertEqual( result, { HC.LOCAL_TAG_SERVICE_IDENTIFIER } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.COMBINED_FILE, ) )
        self.assertEqual( result, { HC.COMBINED_FILE_SERVICE_IDENTIFIER } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.COMBINED_TAG, ) )
        self.assertEqual( result, { HC.COMBINED_TAG_SERVICE_IDENTIFIER } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_FILE, HC.COMBINED_FILE ) )
        self.assertEqual( result, { HC.LOCAL_FILE_SERVICE_IDENTIFIER, HC.COMBINED_FILE_SERVICE_IDENTIFIER } )
        
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
        
        self._db.Write( 'update_services', HC.HIGH_PRIORITY, True, edit_log )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.TAG_REPOSITORY, ) )
        self.assertEqual( result, { new_tag_repo, other_new_tag_repo } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_RATING_LIKE, ) )
        self.assertEqual( result, { new_local_like } )
        
        result = self._db.Read( 'service_identifiers', HC.HIGH_PRIORITY, ( HC.LOCAL_RATING_NUMERICAL, ) )
        self.assertEqual( result, { new_local_numerical } )
        
        #
        
        # should the service key be different or the same?
        other_new_tag_repo_updated = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'a better name' )
        other_new_tag_repo_credentials_updated = CC.Credentials( 'corrected host', 85, access_key = os.urandom( 32 ) )
        
        edit_log = []
        
        edit_log.append( ( HC.DELETE, new_local_like ) )
        edit_log.append( ( HC.EDIT, ( other_new_tag_repo, ( other_new_tag_repo_updated, other_new_tag_repo_credentials_updated, None ) ) ) )
        
        self._db.Write( 'update_services', HC.HIGH_PRIORITY, True, edit_log )
        
        # now delete local_like, test that
        # edit other_tag_repo, test that
        
        #
        
        result = self._db.Read( 'service', HC.HIGH_PRIORITY, new_tag_repo )
        
        # test credentials
        
        result = self._db.Read( 'services', HC.HIGH_PRIORITY, ( HC.TAG_REPOSITORY, ) )
        
        # test there are two, and test credentials
        
    