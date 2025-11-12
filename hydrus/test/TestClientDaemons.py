import os
import shutil
import time
import unittest

from unittest import mock

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTemp

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDaemons
from hydrus.client import ClientLocation
from hydrus.client.exporting import ClientExportingFiles
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing import ClientImportLocal
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import TestGlobals as TG
from hydrus.test import HelperFunctions

with open( HydrusStaticDir.GetStaticPath( 'hydrus.png' ), 'rb' ) as f:
    
    EXAMPLE_FILE = f.read()
    

class TestDaemons( unittest.TestCase ):
    
    def test_export_folders_daemon( self ):
        
        test_dir_source = HydrusTemp.GetSubTempDir( 'export_folder_test_source' )
        test_dir_dest = HydrusTemp.GetSubTempDir( 'export_folder_test_dest' )
        
        try:
            
            # export folder
            # db do search
            # db read metadata
            # client files export with correct filename
            
            HydrusPaths.MakeSureDirectoryExists( test_dir_dest )
            
            fake_file_path = os.path.join( test_dir_source, '0' )
            
            HydrusPaths.MirrorFile( HydrusStaticDir.GetStaticPath( 'hydrus.png' ), fake_file_path )
            
            #
            
            file_search_context = ClientSearchFileSearchContext.FileSearchContext(
                ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
                ClientSearchTagContext.TagContext(),
                predicates = [
                    ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
                ]
            )
            
            export_folder = ClientExportingFiles.ExportFolder(
                'test',
                test_dir_dest,
                file_search_context = file_search_context,
                phrase = '{hash}'
            )
            
            hash_1 = HydrusData.GenerateKey()
            hash_2 = HydrusData.GenerateKey()
            mime = HC.IMAGE_JPEG
            
            fake_media_result_1 = HelperFunctions.GetFakeMediaResult( hash_1, mime )
            fake_media_result_2 = HelperFunctions.GetFakeMediaResult( hash_2, mime )
            
            read_db_side_effect = HelperFunctions.DBSideEffect()
            read_db_side_effect.AddResult( 'serialisable_names', [ 'test' ] )
            read_db_side_effect.AddResult( 'serialisable_named', export_folder )
            read_db_side_effect.AddResult( 'file_query_ids', [ 1, 2 ] )
            read_db_side_effect.AddResult( 'media_results_from_ids', [ fake_media_result_1, fake_media_result_2 ] )
            
            write_db_side_effect = HelperFunctions.DBSideEffect()
            
            write_db_side_effect.AddResult( 'serialisable', None )
            
            with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ) as read_mock_object:
                
                with mock.patch.object( TG.test_controller, 'WriteSynchronous', side_effect = write_db_side_effect ) as write_mock_object:
                    
                    with mock.patch.object( TG.test_controller.client_files_manager, 'GetFilePath', return_value = fake_file_path ) as client_files_mock_object:
                        
                        ClientDaemons.DAEMONCheckExportFolders()
                        
                        time.sleep( 3 )
                        
                        for i in range( 10 ):
                            
                            if HG.export_folders_running:
                                
                                time.sleep( 1 )
                                
                            
                        
                        #
                        
                        all_read_calls = read_mock_object.call_args_list
                        
                        self.assertEqual( len( all_read_calls ), 4 )
                        
                        self.assertEqual( all_read_calls[0].args[0], 'serialisable_names' )
                        self.assertEqual( all_read_calls[0].args[1], 16 )
                        
                        self.assertEqual( all_read_calls[1].args[0], 'serialisable_named' )
                        self.assertEqual( all_read_calls[1].args[1], 16 )
                        self.assertEqual( all_read_calls[1].args[2], 'test' )
                        
                        self.assertEqual( all_read_calls[2].args[0], 'file_query_ids' )
                        self.assertEqual( all_read_calls[2].args[1], file_search_context )
                        self.assertEqual( all_read_calls[2].kwargs[ 'apply_implicit_limit' ], False )
                        
                        self.assertEqual( all_read_calls[3].args[0], 'media_results_from_ids' )
                        self.assertEqual( all_read_calls[3].args[1], [ 1, 2 ] )
                        
                        #
                        
                        all_write_calls = write_mock_object.call_args_list
                        
                        self.assertEqual( len( all_write_calls ), 1 )
                        
                        self.assertEqual( all_write_calls[0].args[0], 'serialisable' )
                        self.assertEqual( all_write_calls[0].args[1], export_folder )
                        
                        #
                        
                        all_client_files_read_calls = client_files_mock_object.call_args_list
                        
                        self.assertEqual( len( all_client_files_read_calls ), 2 )
                        
                        read_hashes = { all_client_files_read_calls[0].args[0], all_client_files_read_calls[1].args[0] }
                        
                        self.assertEqual( read_hashes, { hash_1, hash_2 })
                        
                        self.assertEqual( all_client_files_read_calls[0].args[1], mime )
                        self.assertEqual( all_client_files_read_calls[1].args[1], mime )
                        
                        #
                        
                        self.assertTrue( os.path.exists( os.path.join( test_dir_dest, hash_1.hex() + '.jpg' ) ) )
                        self.assertTrue( os.path.exists( os.path.join( test_dir_dest, hash_2.hex() + '.jpg' ) ) )
                        
                    
                
            
        finally:
            
            shutil.rmtree( test_dir_source )
            shutil.rmtree( test_dir_dest )
            
        
    
    def test_import_folders_daemon( self ):
        
        test_dir = HydrusTemp.GetSubTempDir( 'import_folder_test' )
        
        try:
            
            HydrusPaths.MakeSureDirectoryExists( test_dir )
            
            hydrus_png_path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
            
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
            
            read_db_side_effect = HelperFunctions.DBSideEffect()
            read_db_side_effect.AddResult( 'hash_status', ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            read_db_side_effect.AddResult( 'serialisable_names', [ 'imp' ] )
            read_db_side_effect.AddResult( 'serialisable_named', import_folder )
            
            write_db_side_effect = HelperFunctions.DBSideEffect()
            
            def handle_import_file( *args, **kwargs ):
                
                ( file_import_job, ) = args
                
                if file_import_job.GetHash().hex() == 'a593942cb7ea9ffcd8ccf2f0fa23c338e23bfecd9a3e508dfc0bcf07501ead08': # 'blarg' in sha256 hex
                    
                    raise Exception( 'File failed to import for some reason!' )
                    
                else:
                    
                    h = file_import_job.GetHash()
                    
                    if h is None:
                        
                        h = os.urandom( 32 )
                        
                    
                    return ClientImportFiles.FileImportStatus( CC.STATUS_SUCCESSFUL_AND_NEW, h, note = 'test note' )
                    
                
            
            write_db_side_effect.AddCallable( 'import_file', handle_import_file )
            write_db_side_effect.AddResult( 'serialisable', None )
            
            with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ):
                
                with mock.patch.object( TG.test_controller, 'WriteSynchronous', side_effect = write_db_side_effect ) as write_mock_object:
                    
                    manager = ClientImportLocal.ImportFoldersManager( TG.test_controller )
                    
                    manager.Start()
                    
                    manager.Wake()
                    
                    time.sleep( 3 )
                    
                    for i in range( 10 ):
                        
                        if HG.import_folders_running:
                            
                            time.sleep( 1 )
                            
                        
                    
                    try:
                        
                        all_write_calls = write_mock_object.call_args_list
                        
                        self.assertEqual( len( all_write_calls ), 4 )
                        
                        self.assertEqual( all_write_calls[0].args[0], 'import_file' )
                        self.assertTrue( isinstance( all_write_calls[0].args[1], ClientImportFiles.FileImportJob ) )
                        self.assertEqual( all_write_calls[1].args[0], 'import_file' )
                        self.assertTrue( isinstance( all_write_calls[1].args[1], ClientImportFiles.FileImportJob ) )
                        self.assertEqual( all_write_calls[2].args[0], 'import_file' )
                        self.assertTrue( isinstance( all_write_calls[2].args[1], ClientImportFiles.FileImportJob ) )
                        
                        self.assertEqual( all_write_calls[3].args[0], 'serialisable' )
                        self.assertEqual( all_write_calls[3].args[1], import_folder )
                        
                        self.assertTrue( not os.path.exists( os.path.join( test_dir, '0' ) ) )
                        self.assertTrue( not os.path.exists( os.path.join( test_dir, '1' ) ) )
                        self.assertTrue( not os.path.exists( os.path.join( test_dir, '2' ) ) )
                        self.assertTrue( os.path.exists( os.path.join( test_dir, '3' ) ) )
                        self.assertTrue( os.path.exists( os.path.join( test_dir, '4' ) ) )
                        
                    finally:
                        
                        manager.Shutdown()
                        
                    
                
            
        finally:
            
            shutil.rmtree( test_dir )
            
        
    
