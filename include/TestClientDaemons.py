import ClientDaemons
import collections
import HydrusConstants as HC
import os
import shutil
import stat
import TestConstants
import tempfile
import unittest
import HydrusData
import ClientConstants as CC
import HydrusGlobals
import wx

class TestDaemons( unittest.TestCase ):
    
    def test_import_folders_daemon( self ):
        
        test_dir = tempfile.mkdtemp()
        
        try:
            
            if not os.path.exists( test_dir ): os.mkdir( test_dir )
            
            with open( test_dir + os.path.sep + '0', 'wb' ) as f: f.write( TestConstants.tinest_gif )
            with open( test_dir + os.path.sep + '1', 'wb' ) as f: f.write( TestConstants.tinest_gif ) # previously imported
            with open( test_dir + os.path.sep + '2', 'wb' ) as f: f.write( TestConstants.tinest_gif )
            with open( test_dir + os.path.sep + '3', 'wb' ) as f: f.write( 'blarg' ) # broken
            with open( test_dir + os.path.sep + '4', 'wb' ) as f: f.write( 'blarg' ) # previously failed
            
            #
            
            path = test_dir
            
            details = {}
            
            details[ 'type' ] = HC.IMPORT_FOLDER_TYPE_SYNCHRONISE
            details[ 'cached_imported_paths' ] = { test_dir + os.path.sep + '1' }
            details[ 'failed_imported_paths' ] = { test_dir + os.path.sep + '4' }
            details[ 'local_tag' ] = 'local tag'
            details[ 'last_checked' ] = HydrusData.GetNow() - 1500
            details[ 'check_period' ] = 1000
            
            old_details = dict( details )
            
            wx.GetApp().SetRead( 'import_folders', { path : details } )
            
            ClientDaemons.DAEMONCheckImportFolders()
            
            #(('C:\\code\\Hydrus\\temp\\7baa9a818a14b7a9cbefb04c16bdc45ac651eb7400c1996e66e2efeef9e3ee5d',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            #(('C:\\code\\Hydrus\\temp\\e0dbdcb1a13c0565ffb73f2f497528adbe1703ca1dfc69680202487187b9fcfa',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            #(('C:\\code\\Hydrus\\temp\\182c4eecf2a5b4dfc8b74813bcff5d967ed53d92a982d8ae18520e1504fa5902',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            
            import_file = wx.GetApp().GetWrite( 'import_file' )
            
            self.assertEqual( len( import_file ), 3 )
            
            expected_tag_part = { 'service_keys_to_tags' : { CC.LOCAL_TAG_SERVICE_KEY : set( [ 'local tag' ] ) } }
            
            ( one, two, three ) = import_file
            
            ( temp_path, tag_part ) = one
            
            self.assertEqual( tag_part, expected_tag_part )
            
            ( temp_path, tag_part ) = two
            
            self.assertEqual( tag_part, expected_tag_part )
            
            ( temp_path, tag_part ) = three
            
            self.assertEqual( tag_part, expected_tag_part )
            
            # I need to expand tests here with the new file system
            
            [ ( ( updated_path, updated_details ), kwargs ) ] = wx.GetApp().GetWrite( 'import_folder' )
            
            self.assertEqual( path, updated_path )
            
            self.assertEqual( updated_details[ 'type' ], old_details[ 'type' ] )
            self.assertEqual( updated_details[ 'cached_imported_paths' ], { test_dir + os.path.sep + '0', test_dir + os.path.sep + '1', test_dir + os.path.sep + '2' } )
            self.assertEqual( updated_details[ 'failed_imported_paths' ], { test_dir + os.path.sep + '3', test_dir + os.path.sep + '4' } )
            self.assertEqual( updated_details[ 'local_tag' ], old_details[ 'local_tag' ] )
            self.assertGreater( updated_details[ 'last_checked' ], old_details[ 'last_checked' ] )
            self.assertEqual( updated_details[ 'check_period' ], old_details[ 'check_period' ] )
            
            #
            
            path = test_dir
            
            details = {}
            
            details[ 'type' ] = HC.IMPORT_FOLDER_TYPE_DELETE
            details[ 'cached_imported_paths' ] = set()
            details[ 'failed_imported_paths' ] = { test_dir + os.path.sep + '4' }
            details[ 'local_tag' ] = 'local tag'
            details[ 'last_checked' ] = HydrusData.GetNow() - 1500
            details[ 'check_period' ] = 1000
            
            old_details = dict( details )
            
            wx.GetApp().SetRead( 'import_folders', { path : details } )
            
            ClientDaemons.DAEMONCheckImportFolders()
            
            # improve these tests as above
            
            # old entries
            #(('GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            #(('GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            #(('GIF89a\x01\x00\x01\x00\x00\xff\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x00;',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            #(('blarg',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            
            import_file = wx.GetApp().GetWrite( 'import_file' )
            
            [ ( ( updated_path, updated_details ), kwargs ) ] = wx.GetApp().GetWrite( 'import_folder' )
            
            self.assertEqual( path, updated_path )
            
            self.assertEqual( updated_details[ 'type' ], old_details[ 'type' ] )
            self.assertEqual( updated_details[ 'cached_imported_paths' ], set() )
            self.assertEqual( updated_details[ 'failed_imported_paths' ], { test_dir + os.path.sep + '3', test_dir + os.path.sep + '4' } )
            self.assertEqual( updated_details[ 'local_tag' ], old_details[ 'local_tag' ] )
            self.assertGreater( updated_details[ 'last_checked' ], old_details[ 'last_checked' ] )
            self.assertEqual( updated_details[ 'check_period' ], old_details[ 'check_period' ] )
            
            self.assertTrue( not os.path.exists( test_dir + os.path.sep + '0' ) )
            self.assertTrue( not os.path.exists( test_dir + os.path.sep + '1' ) )
            self.assertTrue( not os.path.exists( test_dir + os.path.sep + '2' ) )
            self.assertTrue( os.path.exists( test_dir + os.path.sep + '3' ) )
            self.assertTrue( os.path.exists( test_dir + os.path.sep + '4' ) )
            
        finally:
            
            shutil.rmtree( test_dir )
            
        
    