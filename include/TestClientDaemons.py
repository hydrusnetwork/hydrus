import ClientDB
import collections
import HydrusConstants as HC
import os
import TestConstants
import unittest

class TestDaemons( unittest.TestCase ):
    
    def test_import_folders_daemon( self ):
        
        test_dir = HC.TEMP_DIR + os.path.sep + 'test'
        
        if not os.path.exists( test_dir ): os.mkdir( test_dir )
        
        with HC.o( test_dir + os.path.sep + '1', 'wb' ) as f: f.write( TestConstants.tinest_gif )
        with HC.o( test_dir + os.path.sep + '2', 'wb' ) as f: f.write( TestConstants.tinest_gif )
        with HC.o( test_dir + os.path.sep + '3', 'wb' ) as f: f.write( TestConstants.tinest_gif )
        with HC.o( test_dir + os.path.sep + '4', 'wb' ) as f: f.write( 'blarg' ) # broken
        with HC.o( test_dir + os.path.sep + '5', 'wb' ) as f: f.write( TestConstants.tinest_gif ) # previously failed for whatever reason
        
        #
        
        path = test_dir
        
        details = {}
        
        details[ 'type' ] = HC.IMPORT_FOLDER_TYPE_SYNCHRONISE
        details[ 'cached_imported_paths' ] = { test_dir + os.path.sep + '2' }
        details[ 'failed_imported_paths' ] = { test_dir + os.path.sep + '5' }
        details[ 'local_tag' ] = 'local tag'
        details[ 'last_checked' ] = HC.GetNow() - 1500
        details[ 'check_period' ] = 1000
        
        old_details = dict( details )
        
        HC.app.SetRead( 'import_folders', [ ( path, details ) ] )
        
        ClientDB.DAEMONCheckImportFolders()
        
        expected_import_file = [(('GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',), {'service_identifiers_to_tags': {HC.LOCAL_TAG_SERVICE_IDENTIFIER: set(['local tag'])}}), (('GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',), {'service_identifiers_to_tags': {HC.LOCAL_TAG_SERVICE_IDENTIFIER: set(['local tag'])}}), (('blarg',), {'service_identifiers_to_tags': {HC.LOCAL_TAG_SERVICE_IDENTIFIER: set(['local tag'])}})]
        
        import_file = HC.app.GetWrite( 'import_file' )
        
        self.assertEqual( import_file, expected_import_file )
        
        [ ( ( updated_path, updated_details ), kwargs ) ] = HC.app.GetWrite( 'import_folder' )
        
        self.assertEqual( path, updated_path )
        
        self.assertEqual( updated_details[ 'type' ], old_details[ 'type' ] )
        self.assertEqual( updated_details[ 'cached_imported_paths' ], { test_dir + os.path.sep + '1', test_dir + os.path.sep + '2', test_dir + os.path.sep + '3' } )
        self.assertEqual( updated_details[ 'failed_imported_paths' ], { test_dir + os.path.sep + '4', test_dir + os.path.sep + '5' } )
        self.assertEqual( updated_details[ 'local_tag' ], old_details[ 'local_tag' ] )
        self.assertGreater( updated_details[ 'last_checked' ], old_details[ 'last_checked' ] )
        self.assertEqual( updated_details[ 'check_period' ], old_details[ 'check_period' ] )
        
        #
        
        path = test_dir
        
        details = {}
        
        details[ 'type' ] = HC.IMPORT_FOLDER_TYPE_DELETE
        details[ 'cached_imported_paths' ] = set()
        details[ 'failed_imported_paths' ] = { test_dir + os.path.sep + '5' }
        details[ 'local_tag' ] = 'local tag'
        details[ 'last_checked' ] = HC.GetNow() - 1500
        details[ 'check_period' ] = 1000
        
        old_details = dict( details )
        
        HC.app.SetRead( 'import_folders', [ ( path, details ) ] )
        
        ClientDB.DAEMONCheckImportFolders()
        
        expected_import_file = [(('GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',), {'service_identifiers_to_tags': {HC.LOCAL_TAG_SERVICE_IDENTIFIER: set(['local tag'])}}), (('GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',), {'service_identifiers_to_tags': {HC.LOCAL_TAG_SERVICE_IDENTIFIER: set(['local tag'])}}), (('GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',), {'service_identifiers_to_tags': {HC.LOCAL_TAG_SERVICE_IDENTIFIER: set(['local tag'])}}), (('blarg',), {'service_identifiers_to_tags': {HC.LOCAL_TAG_SERVICE_IDENTIFIER: set(['local tag'])}})]
        
        import_file = HC.app.GetWrite( 'import_file' )
        
        self.assertEqual( import_file, expected_import_file )
        
        [ ( ( updated_path, updated_details ), kwargs ) ] = HC.app.GetWrite( 'import_folder' )
        
        self.assertEqual( path, updated_path )
        
        self.assertEqual( updated_details[ 'type' ], old_details[ 'type' ] )
        self.assertEqual( updated_details[ 'cached_imported_paths' ], set() )
        self.assertEqual( updated_details[ 'failed_imported_paths' ], { test_dir + os.path.sep + '4', test_dir + os.path.sep + '5' } )
        self.assertEqual( updated_details[ 'local_tag' ], old_details[ 'local_tag' ] )
        self.assertGreater( updated_details[ 'last_checked' ], old_details[ 'last_checked' ] )
        self.assertEqual( updated_details[ 'check_period' ], old_details[ 'check_period' ] )
        
        self.assertTrue( not os.path.exists( test_dir + os.path.sep + '1' ) )
        self.assertTrue( not os.path.exists( test_dir + os.path.sep + '2' ) )
        self.assertTrue( not os.path.exists( test_dir + os.path.sep + '3' ) )
        self.assertTrue( os.path.exists( test_dir + os.path.sep + '4' ) )
        self.assertTrue( os.path.exists( test_dir + os.path.sep + '5' ) )
        
        os.remove( test_dir + os.path.sep + '4' )
        os.remove( test_dir + os.path.sep + '5' )
        
        os.rmdir( test_dir )
        
    