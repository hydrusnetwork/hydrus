from . import ClientDaemons
from . import ClientImporting
from . import ClientImportLocal
from . import ClientPaths
import collections
from . import HydrusConstants as HC
import os
import shutil
import stat
import unittest
from . import HydrusData
from . import ClientConstants as CC
from . import HydrusGlobals as HG
from . import HydrusPaths

with open( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), 'rb' ) as f:
    
    EXAMPLE_FILE = f.read()
    
class TestDaemons( unittest.TestCase ):
    
    def test_import_folders_daemon( self ):
        
        test_dir = HydrusPaths.GetTempDir()
        
        try:
            
            HG.test_controller.SetRead( 'hash_status', ( CC.STATUS_UNKNOWN, None, '' ) )
            
            HydrusPaths.MakeSureDirectoryExists( test_dir )
            
            hydrus_png_path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
            
            HydrusPaths.MirrorFile( hydrus_png_path, os.path.join( test_dir, '0' ) )
            HydrusPaths.MirrorFile( hydrus_png_path, os.path.join( test_dir, '1' ) ) # previously imported
            HydrusPaths.MirrorFile( hydrus_png_path, os.path.join( test_dir, '2' ) )
            
            with open( os.path.join( test_dir, '3' ), 'wb' ) as f: f.write( b'blarg' ) # broken
            with open( os.path.join( test_dir, '4' ), 'wb' ) as f: f.write( b'blarg' ) # previously failed
            
            #
            
            actions = {}
            
            actions[ CC.STATUS_SUCCESSFUL_AND_NEW ] = CC.IMPORT_FOLDER_DELETE
            actions[ CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ] = CC.IMPORT_FOLDER_DELETE
            actions[ CC.STATUS_DELETED ] = CC.IMPORT_FOLDER_DELETE
            actions[ CC.STATUS_ERROR ] = CC.IMPORT_FOLDER_IGNORE
            
            import_folder = ClientImportLocal.ImportFolder( 'imp', path = test_dir, actions = actions )
            
            HG.test_controller.SetRead( 'serialisable_names', [ 'imp' ] )
            HG.test_controller.SetRead( 'serialisable_named', import_folder )
            
            HG.test_controller.ClearWrites( 'import_file' )
            HG.test_controller.ClearWrites( 'serialisable' )
            
            ClientDaemons.DAEMONCheckImportFolders()
            
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
            
        
    
