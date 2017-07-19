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
import HydrusGlobals as HG
import HydrusPaths

with open( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), 'rb' ) as f:
    
    EXAMPLE_FILE = f.read()
    
class TestDaemons( unittest.TestCase ):
    
    def test_import_folders_daemon( self ):
        
        test_dir = tempfile.mkdtemp()
        
        try:
            
            HG.test_controller.SetRead( 'hash_status', CC.STATUS_NEW )
            
            HydrusPaths.MakeSureDirectoryExists( test_dir )
            
            hydrus_png_path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
            
            HydrusPaths.MirrorFile( hydrus_png_path, os.path.join( test_dir, '0' ) )
            HydrusPaths.MirrorFile( hydrus_png_path, os.path.join( test_dir, '1' ) ) # previously imported
            HydrusPaths.MirrorFile( hydrus_png_path, os.path.join( test_dir, '2' ) )
            
            with open( os.path.join( test_dir, '3' ), 'wb' ) as f: f.write( 'blarg' ) # broken
            with open( os.path.join( test_dir, '4' ), 'wb' ) as f: f.write( 'blarg' ) # previously failed
            
            #
            
            import_folder = ClientImporting.ImportFolder( 'imp', path = test_dir )
            
            HG.test_controller.SetRead( 'serialisable_named', [ import_folder ] )
            
            ClientDaemons.DAEMONCheckImportFolders( HG.test_controller )
            
            import_file = HG.test_controller.GetWrite( 'import_file' )
            
            self.assertEqual( len( import_file ), 3 )
            
            # I need to expand tests here with the new file system
            
            [ ( ( updated_import_folder, ), empty_dict ) ] = HG.test_controller.GetWrite( 'serialisable' )
            
            self.assertEqual( updated_import_folder, import_folder )
            
            self.assertTrue( not os.path.exists( os.path.join( test_dir, '0' ) ) )
            self.assertTrue( not os.path.exists( os.path.join( test_dir, '1' ) ) )
            self.assertTrue( not os.path.exists( os.path.join( test_dir, '2' ) ) )
            self.assertTrue( os.path.exists( os.path.join( test_dir, '3' ) ) )
            self.assertTrue( os.path.exists( os.path.join( test_dir, '4' ) ) )
            
        finally:
            
            shutil.rmtree( test_dir )
            
        
    
