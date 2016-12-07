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
import HydrusPaths

with open( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), 'rb' ) as f:
    
    EXAMPLE_FILE = f.read()
    
class TestDaemons( unittest.TestCase ):
    
    def test_import_folders_daemon( self ):
        
        test_dir = tempfile.mkdtemp()
        
        try:
            
            HydrusPaths.MakeSureDirectoryExists( test_dir )
            
            with open( os.path.join( test_dir, '0' ), 'wb' ) as f: f.write( TestConstants.tinest_gif )
            with open( os.path.join( test_dir, '1' ), 'wb' ) as f: f.write( TestConstants.tinest_gif ) # previously imported
            with open( os.path.join( test_dir, '2' ), 'wb' ) as f: f.write( TestConstants.tinest_gif )
            with open( os.path.join( test_dir, '3' ), 'wb' ) as f: f.write( 'blarg' ) # broken
            with open( os.path.join( test_dir, '4' ), 'wb' ) as f: f.write( 'blarg' ) # previously failed
            
            #
            
            import_folder = ClientImporting.ImportFolder( 'imp', path = test_dir )
            
            HydrusGlobals.test_controller.SetRead( 'serialisable_named', [ import_folder ] )
            
            ClientDaemons.DAEMONCheckImportFolders( HydrusGlobals.test_controller )
            
            import_file = HydrusGlobals.test_controller.GetWrite( 'import_file' )
            
            self.assertEqual( len( import_file ), 3 )
            
            # I need to expand tests here with the new file system
            
            [ ( ( updated_import_folder, ), empty_dict ) ] = HydrusGlobals.test_controller.GetWrite( 'serialisable' )
            
            self.assertEqual( updated_import_folder, import_folder )
            
            self.assertTrue( not os.path.exists( os.path.join( test_dir, '0' ) ) )
            self.assertTrue( not os.path.exists( os.path.join( test_dir, '1' ) ) )
            self.assertTrue( not os.path.exists( os.path.join( test_dir, '2' ) ) )
            self.assertTrue( os.path.exists( os.path.join( test_dir, '3' ) ) )
            self.assertTrue( os.path.exists( os.path.join( test_dir, '4' ) ) )
            
        finally:
            
            shutil.rmtree( test_dir )
            
        
    
