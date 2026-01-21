import os
import time
import typing
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusStaticDir

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.db import ClientDB
from hydrus.client.duplicates import ClientDuplicatesAutoResolutionComparators
from hydrus.client.files.images import ClientVisualData
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.importing import ClientImportFiles
from hydrus.client.metadata import ClientMetadataConditional
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import TestController
from hydrus.test import TestGlobals as TG
from hydrus.test import HelperFunctions

class TestComparatorOneFile( unittest.TestCase ):
    
    def test_comparator_1_empty( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_A )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_B )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_EITHER )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_2( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_A )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_B )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        comparator.SetLookingAt( ClientDuplicatesAutoResolutionComparators.LOOKING_AT_EITHER )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    

class TestComparatorRelativeFileInfo( unittest.TestCase ):
    
    def test_comparator_0_flat( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 1.0 )
        comparator.SetDelta( 0 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL
            )
        )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 950
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 1.0 )
        comparator.SetDelta( 0 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 995
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_1_delta( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        # exactly 100 px difference
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 1.0 )
        comparator.SetDelta( 100 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 900
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        # at least 100 px difference to get any Trues
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 1.0 )
        comparator.SetDelta( 100 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 900
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 950
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 850
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_2_multiplier( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        # exactly twice
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 2.0 )
        comparator.SetDelta( 0 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_EQUAL
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 500
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        # at least twice to get any Trues
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 2.0 )
        comparator.SetDelta( 0 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 500
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 600
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 400
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_3_crazy( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        # just for fun
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        comparator.SetMultiplier( 2.0 )
        comparator.SetDelta( 100 )
        
        comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        
        #
        
        media_result_b.GetFileInfoManager().size = media_result_a.GetFileInfoManager().size
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 1000
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 500
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 450
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_a.GetFileInfoManager().size = 1000
        media_result_b.GetFileInfoManager().size = 445
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    

class TestComparatorHardcoded( unittest.TestCase ):
    
    _db: typing.Any = None
    
    @classmethod
    def _clear_db( cls ):
        
        cls._delete_db()
        
        # class variable
        cls._db = ClientDB.DB( TG.test_controller, TestController.DB_DIR, 'client' )
        
        TG.test_controller.SetTestDB( cls._db )
        
    
    @classmethod
    def _delete_db( cls ):
        
        cls._db.Shutdown()
        
        while not cls._db.LoopIsFinished():
            
            time.sleep( 0.1 )
            
        
        db_filenames = list(cls._db._db_filenames.values())
        
        for filename in db_filenames:
            
            path = os.path.join( TestController.DB_DIR, filename )
            
            os.remove( path )
            
        
        del cls._db
        
        TG.test_controller.ClearTestDB()
        
    
    @classmethod
    def setUpClass( cls ):
        
        cls._db = ClientDB.DB( TG.test_controller, TestController.DB_DIR, 'client' )
        
        TG.test_controller.SetTestDB( cls._db )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._delete_db()
        
    
    def _read( self, action, *args, **kwargs ): return TestComparatorHardcoded._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestComparatorHardcoded._db.Write( action, True, *args, **kwargs )
    
    def _do_file_import( self, name ):
        
        path = HydrusStaticDir.GetStaticPath( os.path.join( 'testing', name ) )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        TG.test_controller.client_files_manager.AddFile( file_import_job.GetHash(), file_import_job.GetMime(), file_import_job._temp_path, thumbnail_bytes = file_import_job._thumbnail_bytes )
        
        self._write( 'import_file', file_import_job )
        
        hash = file_import_job.GetHash()
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        return media_result
        
    
    def test_comparator_0_filetypes( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_c = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_c ) )
        self.assertFalse( comparator.Test( media_result_c, media_result_a ) )
        
        #
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_DIFFERS )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_c ) )
        self.assertTrue( comparator.Test( media_result_c, media_result_a ) )
        
    
    def test_comparator_1_exif_and_icc( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        media_result_c = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        media_result_d = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        media_result_a.GetFileInfoManager().has_exif = True
        media_result_b.GetFileInfoManager().has_exif = True
        media_result_c.GetFileInfoManager().has_exif = False
        media_result_d.GetFileInfoManager().has_exif = False
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        self.assertTrue( comparator.Test( media_result_c, media_result_d ) )
        self.assertTrue( comparator.Test( media_result_d, media_result_c ) )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_c ) )
        self.assertFalse( comparator.Test( media_result_c, media_result_a ) )
        
        #
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        media_result_c = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        media_result_d = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey() )
        
        media_result_a.GetFileInfoManager().has_icc_profile = True
        media_result_b.GetFileInfoManager().has_icc_profile = True
        media_result_c.GetFileInfoManager().has_icc_profile = False
        media_result_d.GetFileInfoManager().has_icc_profile = False
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_ICC_PROFILE_SAME )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        self.assertTrue( comparator.Test( media_result_c, media_result_d ) )
        self.assertTrue( comparator.Test( media_result_d, media_result_c ) )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_c ) )
        self.assertFalse( comparator.Test( media_result_c, media_result_a ) )
        
    
    def test_comparator_2_jpeg_quality( self ):
        
        self._clear_db()
        
        media_result_a = self._do_file_import( 'visual_dupe_original.jpg' )
        media_result_b = self._do_file_import( 'visual_dupe_grunky.jpg' )
        
        #
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_A_HAS_CLEARLY_BETTER_JPEG_QUALITY )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        self.assertFalse( comparator.OrderDoesNotMatter() )
        self.assertFalse( comparator.IsFast() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        media_result_c = self._do_file_import( 'muh_png.png' )
        
        self.assertFalse( comparator.Test( media_result_c, media_result_c ) )
        
    

class TestComparatorVisualDuplicates( unittest.TestCase ):
    
    _db: typing.Any = None
    
    @classmethod
    def _clear_db( cls ):
        
        cls._delete_db()
        
        # class variable
        cls._db = ClientDB.DB( TG.test_controller, TestController.DB_DIR, 'client' )
        
        TG.test_controller.SetTestDB( cls._db )
        
    
    @classmethod
    def _delete_db( cls ):
        
        cls._db.Shutdown()
        
        while not cls._db.LoopIsFinished():
            
            time.sleep( 0.1 )
            
        
        db_filenames = list(cls._db._db_filenames.values())
        
        for filename in db_filenames:
            
            path = os.path.join( TestController.DB_DIR, filename )
            
            os.remove( path )
            
        
        del cls._db
        
        TG.test_controller.ClearTestDB()
        
    
    @classmethod
    def setUpClass( cls ):
        
        cls._db = ClientDB.DB( TG.test_controller, TestController.DB_DIR, 'client' )
        
        TG.test_controller.SetTestDB( cls._db )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._delete_db()
        
    
    def _read( self, action, *args, **kwargs ): return TestComparatorVisualDuplicates._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestComparatorVisualDuplicates._db.Write( action, True, *args, **kwargs )
    
    def _do_file_import( self, name ):
        
        path = HydrusStaticDir.GetStaticPath( os.path.join( 'testing', name ) )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        TG.test_controller.client_files_manager.AddFile( file_import_job.GetHash(), file_import_job.GetMime(), file_import_job._temp_path, thumbnail_bytes = file_import_job._thumbnail_bytes )
        
        self._write( 'import_file', file_import_job )
        
        hash = file_import_job.GetHash()
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        return media_result
        
    
    def test_comparator_0_easy( self ):
        
        self._clear_db()
        
        media_result_a = self._do_file_import( 'visual_dupe_original.jpg' )
        media_result_b = self._do_file_import( 'visual_dupe_scale.jpg' )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates( acceptable_confidence = ClientVisualData.VISUAL_DUPLICATES_RESULT_VERY_PROBABLY )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertFalse( comparator.IsFast() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_1_grunky( self ):
        
        self._clear_db()
        
        media_result_a = self._do_file_import( 'visual_dupe_original.jpg' )
        media_result_b = self._do_file_import( 'visual_dupe_grunky.jpg' )
        
        #
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates( acceptable_confidence = ClientVisualData.VISUAL_DUPLICATES_RESULT_VERY_PROBABLY )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertFalse( comparator.IsFast() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
        #
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates( acceptable_confidence = ClientVisualData.VISUAL_DUPLICATES_RESULT_NEAR_PERFECT )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertFalse( comparator.IsFast() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_2_colour( self ):
        
        self._clear_db()
        
        media_result_a = self._do_file_import( 'visual_dupe_original.jpg' )
        media_result_b = self._do_file_import( 'visual_dupe_colour.jpg' )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates( acceptable_confidence = ClientVisualData.VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertFalse( comparator.IsFast() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_3_correction( self ):
        
        self._clear_db()
        
        media_result_a = self._do_file_import( 'visual_dupe_original.jpg' )
        media_result_b = self._do_file_import( 'visual_dupe_correction.jpg' )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeVisualDuplicates( acceptable_confidence = ClientVisualData.VISUAL_DUPLICATES_RESULT_ALMOST_CERTAINLY )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertFalse( comparator.IsFast() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    

class TestComparatorAND( unittest.TestCase ):
    
    def test_comparator_0_empty( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorAND( [] )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertTrue( comparator.IsFast() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_1_true_both_ways( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        media_result_a.GetFileInfoManager().has_exif = True
        media_result_b.GetFileInfoManager().has_exif = True
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorAND(
            [
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME ),
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME )
            ]
        )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertTrue( comparator.IsFast() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_2_false_both_ways( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        media_result_a.GetFileInfoManager().has_exif = True
        media_result_b.GetFileInfoManager().has_exif = True
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorAND(
            [
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME ),
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME )
            ]
        )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertTrue( comparator.IsFast() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_3_true_one_way( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        
        media_result_a.GetFileInfoManager().size = 1500
        media_result_b.GetFileInfoManager().size = 1000
        
        filesize_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        filesize_comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        filesize_comparator.SetMultiplier( 1.0 )
        filesize_comparator.SetDelta( 0 )
        
        filesize_comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorAND(
            [
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME ),
                filesize_comparator
            ]
        )
        
        self.assertTrue( comparator.CanDetermineBetter() )
        self.assertFalse( comparator.OrderDoesNotMatter() )
        self.assertTrue( comparator.IsFast() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    

class TestComparatorOR( unittest.TestCase ):
    
    def test_comparator_0_empty( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOR( [] )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertTrue( comparator.IsFast() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_1_true_both_ways( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        media_result_a.GetFileInfoManager().has_exif = True
        media_result_b.GetFileInfoManager().has_exif = True
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOR(
            [
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME ),
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME )
            ]
        )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertTrue( comparator.IsFast() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertTrue( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_2_false_both_ways( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        media_result_a.GetFileInfoManager().has_exif = False
        media_result_b.GetFileInfoManager().has_exif = True
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOR(
            [
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME ),
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_HAS_EXIF_SAME )
            ]
        )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertTrue( comparator.OrderDoesNotMatter() )
        self.assertTrue( comparator.IsFast() )
        
        self.assertFalse( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    
    def test_comparator_3_true_one_way( self ):
        
        media_result_a = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_b = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        media_result_a.GetFileInfoManager().size = 1500
        media_result_b.GetFileInfoManager().size = 1000
        
        filesize_comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeFileInfo()
        
        filesize_comparator.SetSystemPredicate(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE
            )
        )
        
        filesize_comparator.SetMultiplier( 1.0 )
        filesize_comparator.SetDelta( 0 )
        
        filesize_comparator.SetNumberTest(
            ClientNumberTest.NumberTest(
                operator = ClientNumberTest.NUMBER_TEST_OPERATOR_GREATER_THAN
            )
        )
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOR(
            [
                ClientDuplicatesAutoResolutionComparators.PairComparatorRelativeHardcoded( hardcoded_type = ClientDuplicatesAutoResolutionComparators.HARDCODED_COMPARATOR_TYPE_FILETYPE_SAME ),
                filesize_comparator
            ]
        )
        
        self.assertFalse( comparator.CanDetermineBetter() )
        self.assertFalse( comparator.OrderDoesNotMatter() )
        self.assertTrue( comparator.IsFast() )
        
        self.assertTrue( comparator.Test( media_result_a, media_result_b ) )
        self.assertFalse( comparator.Test( media_result_b, media_result_a ) )
        
    

class TestSelector( unittest.TestCase ):
    
    def test_selector_empty( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        self.assertTrue( selector.MatchingPairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertTrue( selector.MatchingPairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_one_way_around( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        self.assertFalse( selector.MatchingPairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_both_ways_around( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 5 ) )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        self.assertTrue( selector.MatchingPairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        self.assertTrue( selector.MatchingPairMatchesBothWaysAround( media_result_2, media_result_1 ) )
        
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )
        self.assertEqual( { media_result_1, media_result_2 }, set( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
    def test_selector_no_match( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 5000000 ) )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        self.assertEqual( None, selector.GetMatchingAB( media_result_1, media_result_2 ) )
        self.assertEqual( None, selector.GetMatchingAB( media_result_2, media_result_1 ) )
        
    
    def test_multiple_comparators_fail( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator_1 = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 5000000 ) )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator_1.SetMetadataConditional( mc )
        
        comparator_2 = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator_2.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator_1, comparator_2 ] )
        
        self.assertEqual( None, selector.GetMatchingAB( media_result_1, media_result_2 ) )
        self.assertEqual( None, selector.GetMatchingAB( media_result_2, media_result_1 ) )
        
    
    def test_multiple_comparators_success( self ):
        
        media_result_1 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_JPEG )
        media_result_2 = HelperFunctions.GetFakeMediaResult( HydrusData.GenerateKey(), mime = HC.IMAGE_PNG )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator_1 = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 5 ) )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator_1.SetMetadataConditional( mc )
        
        comparator_2 = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator_2.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator_1, comparator_2 ] )
        
        self.assertFalse( selector.MatchingPairMatchesBothWaysAround( media_result_1, media_result_2 ) )
        
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_1, media_result_2 ) ) )    
        self.assertEqual( [ media_result_1, media_result_2 ], list( selector.GetMatchingAB( media_result_2, media_result_1 ) ) )
        
    
