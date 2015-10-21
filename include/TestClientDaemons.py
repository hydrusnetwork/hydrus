import ClientDaemons
import ClientImporting
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
            
            import_folder = ClientImporting.ImportFolder( 'imp', path = test_dir, tag = 'local tag' )
            
            HydrusGlobals.test_controller.SetRead( 'serialisable_named', [ import_folder ] )
            
            
            
            ClientDaemons.DAEMONCheckImportFolders()
            
            #(('C:\\code\\Hydrus\\temp\\7baa9a818a14b7a9cbefb04c16bdc45ac651eb7400c1996e66e2efeef9e3ee5d',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            #(('C:\\code\\Hydrus\\temp\\e0dbdcb1a13c0565ffb73f2f497528adbe1703ca1dfc69680202487187b9fcfa',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            #(('C:\\code\\Hydrus\\temp\\182c4eecf2a5b4dfc8b74813bcff5d967ed53d92a982d8ae18520e1504fa5902',), {'service_keys_to_tags': {HC.LOCAL_TAG_SERVICE_KEY: set(['local tag'])}})
            
            import_file = HydrusGlobals.test_controller.GetWrite( 'import_file' )
            
            self.assertEqual( len( import_file ), 3 )
            
            # I need to expand tests here with the new file system
            
            [ ( ( updated_import_folder, ), empty_dict ) ] = HydrusGlobals.test_controller.GetWrite( 'serialisable' )
            
            self.assertEqual( updated_import_folder, import_folder )
            
            self.assertTrue( not os.path.exists( test_dir + os.path.sep + '0' ) )
            self.assertTrue( not os.path.exists( test_dir + os.path.sep + '1' ) )
            self.assertTrue( not os.path.exists( test_dir + os.path.sep + '2' ) )
            self.assertTrue( os.path.exists( test_dir + os.path.sep + '3' ) )
            self.assertTrue( os.path.exists( test_dir + os.path.sep + '4' ) )
            
        finally:
            
            shutil.rmtree( test_dir )
            
        
    