import os
import time
import typing
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusSerialisable
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFilesPhysicalStorage
from hydrus.core.files.images import HydrusImageHandling
from hydrus.core.networking import HydrusNetwork

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client import ClientLocation
from hydrus.client import ClientServices
from hydrus.client.db import ClientDB
from hydrus.client.exporting import ClientExportingFiles
from hydrus.client.files import ClientFilesPhysical
from hydrus.client.files.images import ClientImagePerceptualHashes
from hydrus.client.gui.pages import ClientGUIPageManager
from hydrus.client.gui.pages import ClientGUISession
from hydrus.client.importing import ClientImportLocal
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.search import ClientNumberTest
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import TestController
from hydrus.test import TestGlobals as TG

class TestClientDB( unittest.TestCase ):
    
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
        
    
    def _read( self, action, *args, **kwargs ): return TestClientDB._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestClientDB._db.Write( action, True, *args, **kwargs )
    
    def test_autocomplete( self ):
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY )
        tag_context = ClientSearchTagContext.TagContext( service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY )
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context )
        
        TestClientDB._clear_db()
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'c*' )
        
        self.assertEqual( result, [] )
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'series:*' )
        
        self.assertEqual( result, [] )
        
        #
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        content_updates = []

        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ) )
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        # cars
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'c*' )
        
        preds = set()
        
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'series:cars', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'car', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        
        for p in result: self.assertEqual( p.GetCount().GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'ser*' )
        
        self.assertEqual( result, [] )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'series:c*' )
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'series:cars', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) )
        
        ( read_pred, ) = result
        
        self.assertEqual( read_pred.GetCount().GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'car', exact_match = True )
        
        pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'car', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) )
        
        ( read_pred, ) = result
        
        self.assertEqual( read_pred.GetCount().GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( pred, read_pred )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'c', exact_match = True )
        
        self.assertEqual( result, [] )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = '*' )
        
        preds = set()
        
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'car', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'series:cars', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'maker:ford', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        
        for p in result: self.assertEqual( p.GetCount().GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'series:*' )
        
        preds = set()
        
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'series:cars', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        
        for p in result: self.assertEqual( p.GetCount().GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'c*r*' )
        
        preds = set()
        
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'car', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'series:cars', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        
        for p in result: self.assertEqual( p.GetCount().GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
        #
        
        result = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, file_search_context, search_text = 'ser*', search_namespaces_into_full_tags = True )
        
        preds = set()
        
        preds.add( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'series:cars', count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        
        for p in result: self.assertEqual( p.GetCount().GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        
        self.assertEqual( set( result ), preds )
        
    
    def test_export_folders( self ):
        
        tag_context = ClientSearchTagContext.TagContext( service_key = HydrusData.GenerateKey() )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( HydrusData.GenerateKey() )
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'test' ) ] )
        
        export_folder = ClientExportingFiles.ExportFolder( 'test path', export_type = HC.EXPORT_FOLDER_TYPE_REGULAR, delete_from_client_after_export = False, file_search_context = file_search_context, period = 3600, phrase = '{hash}' )
        
        self._write( 'serialisable', export_folder )
        
        [ result ] = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_EXPORT_FOLDER )
        
        self.assertEqual( result.GetName(), export_folder.GetName() )
        
    
    def test_file_query_ids( self ):
        
        TestClientDB._clear_db()
        
        def run_namespace_predicate_tests( tests ):
            
            for ( inclusive, namespace, result ) in tests:
                
                predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_NAMESPACE, namespace, inclusive ) ]
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
                
                search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                for file_query_id in file_query_ids:
                    
                    self.assertEqual( type( file_query_id ), int )
                    
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_system_predicate_tests( tests ):
            
            for ( predicate_type, info, result ) in tests:
                
                predicates = [ ClientSearchPredicate.Predicate( predicate_type, info ) ]
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
                
                search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                for file_query_id in file_query_ids:
                    
                    self.assertEqual( type( file_query_id ), int )
                    
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_tag_predicate_tests( tests ):
            
            for ( inclusive, tag, result ) in tests:
                
                predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag, inclusive ) ]
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
                
                search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                for file_query_id in file_query_ids:
                    
                    self.assertEqual( type( file_query_id ), int )
                    
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        def run_or_predicate_tests( tests ):
            
            for ( predicates, result ) in tests:
                
                location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
                
                search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = predicates )
                
                file_query_ids = self._read( 'file_query_ids', search_context )
                
                for file_query_id in file_query_ids:
                    
                    self.assertEqual( type( file_query_id ), int )
                    
                
                self.assertEqual( len( file_query_ids ), result )
                
            
        
        tests = []
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LOCAL, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        file_import_status = self._write( 'import_file', file_import_job )
        
        written_status = file_import_status.status
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_SUCCESSFUL_AND_NEW )
        self.assertEqual( written_note, '' )
        self.assertEqual( file_import_job.GetHash(), hash )
        
        time.sleep( 1.1 ) # to get timestamps right
        
        #
        
        tests = []
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( '<', 'delta', ( 1, 1, 1, 1, ) ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( '<', 'delta', ( 0, 0, 0, 0, ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( HC.UNICODE_APPROX_EQUAL, 'delta', ( 1, 1, 1, 1, ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( HC.UNICODE_APPROX_EQUAL, 'delta', ( 0, 0, 0, 0, ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( '>', 'delta', ( 1, 1, 1, 1, ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_IMPORT_TIME, ( '>', 'delta', ( 0, 0, 0, 0, ) ), 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 100, ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 0, ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 100, ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 0, ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 100, ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0, ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 100, ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0, ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_DELETED, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PETITIONED, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_DELETED, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_PETITIONED, CC.LOCAL_FILE_SERVICE_KEY ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True, 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False, 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, True, 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, False, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, True, 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_EXIF, False, 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, True, 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, False, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, True, 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, False, 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, True, 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, False, 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, ( ( hash, ), 'sha256' ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, ( ( bytes.fromhex( '0123456789abcdef' * 4 ), ), 'sha256' ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 201 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 200 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 200 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 60 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 200 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 200 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 199 ), 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX, None, 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LOCAL, None, 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, HC.IMAGES, 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, ( HC.IMAGE_PNG, ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, ( HC.IMAGE_JPEG, ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, HC.VIDEO, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '=', 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '=', 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '>', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '=', 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '=', 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '>', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 1, 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 4, 3 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( HC.UNICODE_APPROX_EQUAL, 1, 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( HC.UNICODE_APPROX_EQUAL, 200, 201 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATIO, ( HC.UNICODE_APPROX_EQUAL, 4, 1 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES, ( ( hash, ), 5 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES, ( ( bytes.fromhex( '0123456789abcdef' * 4 ), ), 5 ), 0 ) )
        
        pixel_hash = HydrusImageHandling.GetImagePixelHash( path, HC.IMAGE_PNG )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA, ( ( pixel_hash, ), (), 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA, ( ( os.urandom( 32 ), ), (), 0 ), 0 ) )
        
        perceptual_hashes = ClientImagePerceptualHashes.GenerateUsefulShapePerceptualHashes( path, HC.IMAGE_PNG )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA, ( (), tuple( perceptual_hashes ), 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA, ( (), ( os.urandom( 32 ), ), 0 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 0, HydrusNumbers.UnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 5270, HydrusNumbers.UnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '<', 5271, HydrusNumbers.UnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '=', 5270, HydrusNumbers.UnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '=', 0, HydrusNumbers.UnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( HC.UNICODE_APPROX_EQUAL, 5270, HydrusNumbers.UnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( HC.UNICODE_APPROX_EQUAL, 0, HydrusNumbers.UnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5270, HydrusNumbers.UnitToInt( 'B' ) ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5269, HydrusNumbers.UnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusNumbers.UnitToInt( 'B' ) ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusNumbers.UnitToInt( 'KB' ) ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusNumbers.UnitToInt( 'MB' ) ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 0, HydrusNumbers.UnitToInt( 'GB' ) ), 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 201 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 200 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 200 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 60 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( HC.UNICODE_APPROX_EQUAL, 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 200 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '=', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 200 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_WIDTH, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '>', 199 ), 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, 100, 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, 1, 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, 0, 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        content_update_package.AddContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, ( hash, ) ) )
        content_update_package.AddContentUpdate( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'car', ( hash, ) ) ) )
        
        self._write( 'content_updates', content_update_package )
        
        time.sleep( 0.5 )
        
        #
        
        tests = []
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 1 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 2 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '=', 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 2 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '=', 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '=', 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '>', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '>', 1 ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 2 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 1 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '<', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '=', 0 ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '=', 1 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '>', 0 ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '', '>', 1 ), 0 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        tests = []
        
        tests.append( ( True, 'car', 1 ) )
        tests.append( ( False, 'car', 0 ) )
        tests.append( ( True, 'bus', 0 ) )
        tests.append( ( False, 'bus', 1 ) )
        
        run_tag_predicate_tests( tests )
        
        #
        
        tests = []
        
        tests.append( ( True, 'series', 0 ) )
        tests.append( ( False, 'series', 1 ) )
        
        run_namespace_predicate_tests( tests )
        
        #
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        content_updates = []
        
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:cars', ( hash, ) ) ) )
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'maker:ford', ( hash, ) ) ) )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        tests = []
        
        tests.append( ( True, 'maker:ford', 1 ) )
        tests.append( ( True, 'ford', 0 ) )
        tests.append( ( False, 'maker:ford', 0 ) )
        tests.append( ( False, 'ford', 1 ) )
        
        run_tag_predicate_tests( tests )
        
        #
        
        tests = []
        
        tests.append( ( True, 'series', 1 ) )
        tests.append( ( False, 'series', 0 ) )
        
        run_namespace_predicate_tests( tests )
        
        #
        
        tests = []
        
        preds = []
        
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientNumberTest.NumberTest.STATICCreateFromCharacters( '<', 201 ) ) )
        
        or_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'truck' ) )
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 0 ) )
        
        preds = []
        
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'truck', inclusive = False ) )
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'bus' ) )
        
        or_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred ], 1 ) )
        
        preds = []
        
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'car' ) )
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'truck' ) )
        
        or_pred_1 = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        preds = []
        
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'maker:toyota' ) )
        preds.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'maker:ford' ) )
        
        or_pred_2 = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER, preds )
        
        tests.append( ( [ or_pred_1, or_pred_2 ], 1 ) )
        
        run_or_predicate_tests( tests )
        
        #
        
        from hydrus.test import TestController
        
        services = self._read( 'services' )
        
        services.append( ClientServices.GenerateService( TestController.LOCAL_RATING_LIKE_SERVICE_KEY, HC.LOCAL_RATING_LIKE, 'test like rating service' ) )
        services.append( ClientServices.GenerateService( TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY, HC.LOCAL_RATING_NUMERICAL, 'test numerical rating service' ) )
        services.append( ClientServices.GenerateService( TestController.LOCAL_RATING_INCDEC_SERVICE_KEY, HC.LOCAL_RATING_INCDEC, 'test inc/dec rating service' ) )
        
        self._write( 'update_services', services )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        content_updates = []
        
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, ( hash, ) ) ) )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TestController.LOCAL_RATING_LIKE_SERVICE_KEY, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        content_updates = []
        
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.6, ( hash, ) ) ) )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        content_updates = []
        
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 3, ( hash, ) ) ) )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TestController.LOCAL_RATING_INCDEC_SERVICE_KEY, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        tests = []
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 1.0, TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 0.0, TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'rated', TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'not rated', TestController.LOCAL_RATING_LIKE_SERVICE_KEY ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 0.6, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 1.0, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.6, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.4, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '<', 0.7, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '<', 0.6, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'rated', TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 'not rated', TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ), 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 3, TestController.LOCAL_RATING_INCDEC_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '=', 1, TestController.LOCAL_RATING_INCDEC_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 3, TestController.LOCAL_RATING_INCDEC_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 2, TestController.LOCAL_RATING_INCDEC_SERVICE_KEY ), 1 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '<', 3, TestController.LOCAL_RATING_INCDEC_SERVICE_KEY ), 0 ) )
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '<', 4, TestController.LOCAL_RATING_INCDEC_SERVICE_KEY ), 1 ) )
        
        run_system_predicate_tests( tests )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_FILE_SERVICE_KEY, content_update )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        tests = []
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LOCAL, None, 0 ) )
        
        tests.append( ( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, None, 0 ) )
        
        run_system_predicate_tests( tests )
        
    
    def test_file_system_predicates( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), tag_context = ClientSearchTagContext.TagContext() )
        
        result = self._read( 'file_system_predicates', file_search_context )
        
        predicates = []
        
        predicates.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING, count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        predicates.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_INBOX, count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 1 ) ) )
        predicates.append( ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE, count = ClientSearchPredicate.PredicateCount.STATICCreateCurrentCount( 0 ) ) )
        predicates.extend( [ ClientSearchPredicate.Predicate( predicate_type ) for predicate_type in [ ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_LIMIT, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TIME, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_URLS, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_PROPERTIES, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_HASH, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DIMENSIONS, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_DURATION, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NOTES, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_ADVANCED, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS, ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS ] ] )
        
        self.assertEqual( set( result ), set( predicates ) )
        
        for i in range( len( predicates ) ): self.assertEqual( result[i].GetCount().GetMinCount(), predicates[i].GetCount().GetMinCount() )
        
    
    def test_file_updates( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = bytes.fromhex( 'fdadb2cae78f2dfeb629449cd005f2a2' )
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        hash_id = media_result.GetHashId()
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertFalse( locations_manager.IsLocal() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db.modules_media_results._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertTrue( locations_manager.IsLocal() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertTrue( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db.modules_media_results._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_FILE_SERVICE_KEY, content_update )
        
        self._write( 'content_updates', content_update_package )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertTrue( locations_manager.IsLocal() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertTrue( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertTrue( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db.modules_media_results._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, ( hash, ), reason = 'test delete' )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_FILE_SERVICE_KEY, content_update )
        
        self._write( 'content_updates', content_update_package )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertTrue( locations_manager.IsLocal() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertTrue( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db.modules_media_results._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
        
        self._write( 'content_updates', content_update_package )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertFalse( locations_manager.IsLocal() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db.modules_media_results._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = bytes.fromhex( 'fdadb2cae78f2dfeb629449cd005f2a2' )
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        hash_id = media_result.GetHashId()
        
        self._db.modules_media_results._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
        #
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_FILE_SERVICE_KEY, content_update )
        
        self._write( 'content_updates', content_update_package )
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
        
        self._write( 'content_updates', content_update_package )
        
        ( media_result, ) = self._read( 'media_results', ( hash, ) )
        
        locations_manager = media_result.GetLocationsManager()
        
        self.assertFalse( locations_manager.IsLocal() )
        self.assertFalse( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.LOCAL_FILE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertTrue( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY in locations_manager.GetDeleted() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetCurrent() )
        self.assertFalse( CC.TRASH_SERVICE_KEY in locations_manager.GetDeleted() )
        
        self._db.modules_media_results._weakref_media_result_cache.DropMediaResult( hash_id, hash )
        
    
    def test_filter_existing_tags( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        #
        
        services = list( self._read( 'services' ) )
        
        new_service_key = HydrusData.GenerateKey()
        
        services.append( ClientServices.GenerateService( new_service_key, HC.LOCAL_TAG, 'new service' ) )
        
        empty_service_key = HydrusData.GenerateKey()
        
        services.append( ClientServices.GenerateService( empty_service_key, HC.LOCAL_TAG, 'empty service' ) )
        
        self._write( 'update_services', services )
        
        #
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        content_updates = []
        
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'character:samus aran', ( hash, ) ) ) )
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'series:metroid', ( hash, ) ) ) )
        
        content_update_package.AddContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_updates )
        
        content_updates = []
        
        content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'clothing:bodysuit', ( hash, ) ) ) )
        
        content_update_package.AddContentUpdates( new_service_key, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        result = self._read( 'filter_existing_tags', CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, { 'character:samus aran', 'series:metroid', 'clothing:bodysuit' } )
        
        self.assertEqual( result, { 'character:samus aran', 'series:metroid' } )
        
        result = self._read( 'filter_existing_tags', new_service_key, { 'character:samus aran', 'series:metroid', 'clothing:bodysuit' } )
        
        self.assertEqual( result, { 'clothing:bodysuit' } )
        
        result = self._read( 'filter_existing_tags', empty_service_key, { 'character:samus aran', 'series:metroid', 'clothing:bodysuit' } )
        
        self.assertEqual( result, set() )
        
    
    def test_gui_sessions( self ):
        
        page_containers = []
        hashes_to_page_data = {}
        
        #
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportGallery()
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportMultipleWatcher()
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        service_keys_to_tags = ClientTags.ServiceKeysToTags( { HydrusData.GenerateKey() : [ 'some', 'tags' ] } )
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportHDD( [ 'some', 'paths' ], FileImportOptionsLegacy.FileImportOptionsLegacy(), [], { 'paths' : service_keys_to_tags }, True )
        
        page_manager.GetVariable( 'hdd_import' ).PausePlay() # to stop trying to import 'some' 'paths'
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        page_manager = ClientGUIPageManager.CreatePageManagerImportSimpleDownloader()
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        page_manager = ClientGUIPageManager.CreatePageManagerPetitions( TG.test_controller.example_tag_repo_service_key )
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
        fsc = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = [] )
        
        page_manager = ClientGUIPageManager.CreatePageManagerQuery( 'search', fsc )
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        tag_context = ClientSearchTagContext.TagContext( service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
        fsc = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, tag_context = tag_context, predicates = [] )
        
        page_manager = ClientGUIPageManager.CreatePageManagerQuery( 'search', fsc )
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [ HydrusData.GenerateKey() for i in range( 200 ) ] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
        fsc = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = [ ClientSearchPredicate.SYSTEM_PREDICATE_ARCHIVE ] )
        
        page_manager = ClientGUIPageManager.CreatePageManagerQuery( 'files', fsc )
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
        fsc = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'tag', count = ClientSearchPredicate.PredicateCount.STATICCreateStaticCount( 1, 3 ) ) ] )
        
        page_manager = ClientGUIPageManager.CreatePageManagerQuery( 'wew lad', fsc )
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
        fsc = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.2, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ) ), ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ) ) ] )
        
        page_manager = ClientGUIPageManager.CreatePageManagerQuery( 'files', fsc )
        
        page_name = page_manager.GetPageName()
        
        page_data = ClientGUISession.GUISessionPageData( page_manager, [] )
        
        page_data_hash = page_data.GetSerialisedHash()
        
        page_container = ClientGUISession.GUISessionContainerPageSingle( page_name, page_data_hash = page_data_hash )
        
        page_containers.append( page_container )
        
        hashes_to_page_data[ page_data_hash ] = page_data
        
        #
        
        top_notebook_container = ClientGUISession.GUISessionContainerPageNotebook( 'top notebook', page_containers = page_containers)
        
        session = ClientGUISession.GUISessionContainer( 'test_session', top_notebook_container = top_notebook_container, hashes_to_page_data = hashes_to_page_data )
        
        self.assertTrue( session.HasAllPageData() )
        
        self._write( 'serialisable', session )
        
        loaded_session = self._read( 'gui_session', 'test_session' )
        
        self.assertTrue( loaded_session.HasAllPageData() )
        
        page_names = []
        
        for page_container in loaded_session.GetTopNotebook().GetPageContainers():
            
            page_names.append( page_container.GetName() )
            
        
        self.assertEqual( page_names, [ 'gallery', 'watcher', 'import', 'simple downloader', 'example tag repo petitions', 'search', 'search', 'files', 'wew lad', 'files' ] )
        
        
    
    def test_import( self ):
        
        TestClientDB._clear_db()
        
        test_files = []
        
        test_files.append( ( 'muh_swf.swf', 'edfef9905fdecde38e0752a5b6ab7b6df887c3968d4246adc9cffc997e168cdf', 456774, HC.APPLICATION_FLASH, 400, 400, { 33 }, { 1 }, True, None ) )
        test_files.append( ( 'muh_mp4.mp4', '2fa293907144a046d043d74e9570b1c792cbfd77ee3f5c93b2b1a1cb3e4c7383', 570534, HC.VIDEO_MP4, 480, 480, { 6266, 6290 }, { 151 }, True, None ) )
        test_files.append( ( 'muh_mpeg.mpeg', 'aebb10aaf3b27a5878fd2732ea28aaef7bbecef7449eaa759421c4ba4efff494', 772096, HC.VIDEO_MPEG, 657, 480, { 3490, 3500 }, { 105 }, False, None ) ) # not actually 720, as this has mickey-mouse SAR, it turns out
        test_files.append( ( 'muh_webm.webm', '55b6ce9d067326bf4b2fbe66b8f51f366bc6e5f776ba691b0351364383c43fcb', 84069, HC.VIDEO_WEBM, 640, 360, { 4010 }, { 120 }, True, None ) )
        test_files.append( ( 'muh_jpg.jpg', '5d884d84813beeebd59a35e474fa3e4742d0f2b6679faa7609b245ddbbd05444', 42296, HC.IMAGE_JPEG, 392, 498, { None }, { None }, False, None ) )
        test_files.append( ( 'muh_png.png', 'cdc67d3b377e6e1397ffa55edc5b50f6bdf4482c7a6102c6f27fa351429d6f49', 31452, HC.IMAGE_PNG, 191, 196, { None }, { None }, False, None ) )
        test_files.append( ( 'muh_apng.png', '9e7b8b5abc7cb11da32db05671ce926a2a2b701415d1b2cb77a28deea51010c3', 616956, HC.ANIMATION_APNG, 500, 500, { 3133, 1880, 1125, 1800 }, { 27, 47 }, False, None ) )
        test_files.append( ( 'muh_gif.gif', '00dd9e9611ebc929bfc78fde99a0c92800bbb09b9d18e0946cea94c099b211c2', 15660, HC.ANIMATION_GIF, 329, 302, { 600 }, { 5 }, False, None ) )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        for ( filename, hex_hash, size, mime, width, height, durations, possible_num_frames, has_audio, num_words ) in test_files:
            
            TG.test_controller.SetRead( 'hash_status', ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            
            path = HydrusStaticDir.GetStaticPath( os.path.join( 'testing', filename ) )
            
            hash = bytes.fromhex( hex_hash )
            
            file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
            
            file_import_job.GeneratePreImportHashAndStatus()
            
            file_import_job.GenerateInfo()
            
            file_import_status = self._write( 'import_file', file_import_job )
            
            written_status = file_import_status.status
            written_hash = file_import_job.GetHash()
            written_note = file_import_status.note
            
            self.assertEqual( written_status, CC.STATUS_SUCCESSFUL_AND_NEW )
            self.assertEqual( written_note, '' )
            self.assertEqual( file_import_job.GetHash(), hash )
            
            media_result = self._read( 'media_result', written_hash )
            
            ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
            
            ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_has_audio, mr_num_words ) = mr_file_info_manager.ToTuple()
            
            mr_inbox = mr_locations_manager.inbox
            
            now = HydrusTime.GetNow()
            
            self.assertEqual( mr_hash, hash )
            self.assertEqual( mr_inbox, True )
            self.assertEqual( mr_size, size )
            self.assertEqual( mr_mime, mime )
            self.assertEqual( mr_width, width )
            self.assertEqual( mr_height, height )
            
            if mr_duration is None:
                
                self.assertIn( mr_duration, durations )
                
            else:
                
                duration_tests = { duration * 0.8 <= mr_duration <= duration * 1.2 for duration in durations }
                
                self.assertIn( True, duration_tests )
                
            
            if mr_num_frames is None:
                
                self.assertIn( mr_num_frames, possible_num_frames )
                
            else:
                
                num_frames_tests = { num_frames * 0.8 <= mr_num_frames <= num_frames * 1.2 for num_frames in possible_num_frames }
                
                self.assertIn( True, num_frames_tests )
                
            
            self.assertEqual( mr_has_audio, has_audio )
            self.assertEqual( mr_num_words, num_words )
            
        
    
    def test_import_folders( self ):
        
        import_folder_1 = ClientImportLocal.ImportFolder( 'imp 1', path = TestController.DB_DIR, publish_files_to_popup_button = False )
        import_folder_2 = ClientImportLocal.ImportFolder( 'imp 2', path = TestController.DB_DIR, period = 1200, publish_files_to_popup_button = False )
        
        #
        
        result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
        
        self.assertEqual( result, [] )
        
        #
        
        self._write( 'serialisable', import_folder_1 )
        self._write( 'serialisable', import_folder_2 )
        
        result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
        
        for item in result:
            
            self.assertEqual( type( item ), ClientImportLocal.ImportFolder )
            
        
        #
        
        self._write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER, 'imp 2' )
        
        result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_IMPORT_FOLDER )
        
        ( item, ) = result
        
        self.assertEqual( item.GetName(), 'imp 1' )
        
    
    def test_init( self ):
        
        self.assertTrue( os.path.exists( TestController.DB_DIR ) )
        
        self.assertTrue( os.path.exists( os.path.join( TestController.DB_DIR, 'client.db' ) ) )
        
        client_files_default = os.path.join( TestController.DB_DIR, 'client_files' )
        
        self.assertTrue( os.path.exists( client_files_default ) )
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( client_files_default, 1 )
        
        for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( 'f', HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ):
            
            subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
            
            self.assertTrue( os.path.exists( subfolder.path ) )
            self.assertTrue( subfolder.PathExists() )
            
        
        for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( 't', HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ):
            
            subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
            
            self.assertTrue( os.path.exists( subfolder.path ) )
            self.assertTrue( subfolder.PathExists() )
            
        
    
    def test_hash_status( self ):
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = bytes.fromhex( 'fdadb2cae78f2dfeb629449cd005f2a2' )
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_UNKNOWN )
        self.assertEqual( written_hash, None )
        
        #
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        # would be redundant, but sometimes(?) triggers the 'it is missing from db' hook
        self.assertIn( written_status, ( CC.STATUS_UNKNOWN, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ) )
        self.assertEqual( written_hash, hash )
        if written_status == CC.STATUS_UNKNOWN:
            
            self.assertIn( 'already in the db', written_note )
            
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_FILE_SERVICE_KEY, content_update )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_DELETED )
        self.assertEqual( written_hash, hash )
        
        # now physical delete
        
        TestClientDB._clear_db()
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        md5 = bytes.fromhex( 'fdadb2cae78f2dfeb629449cd005f2a2' )
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_UNKNOWN )
        self.assertEqual( written_hash, None )
        
        #
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        # would be redundant, but sometimes(?) triggers the 'it is missing from db' hook
        self.assertIn( written_status, ( CC.STATUS_UNKNOWN, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ) )
        self.assertEqual( written_hash, hash )
        if written_status == CC.STATUS_UNKNOWN:
            
            self.assertIn( 'already in the db', written_note )
            
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, ( hash, ), reason = 'test delete' )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, content_update )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        file_import_status = self._read( 'hash_status', 'md5', md5 )
        
        written_status = file_import_status.status
        written_hash = file_import_status.hash
        written_note = file_import_status.note
        
        self.assertEqual( written_status, CC.STATUS_DELETED )
        self.assertEqual( written_hash, hash )
        
    
    def test_media_results( self ):
        
        TestClientDB._clear_db()
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
        
        file_import_job.GeneratePreImportHashAndStatus()
        
        file_import_job.GenerateInfo()
        
        self._write( 'import_file', file_import_job )
        
        hash = file_import_job.GetHash()
        
        #
        
        media_result = self._read( 'media_result', hash )
        
        ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
        
        ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_has_audio, mr_num_words ) = mr_file_info_manager.ToTuple()
        
        mr_inbox = mr_locations_manager.inbox
        
        now = HydrusTime.GetNow()
        
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_inbox, True )
        self.assertEqual( mr_size, 5270 )
        self.assertEqual( mr_mime, HC.IMAGE_PNG )
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_width, 200 )
        self.assertEqual( mr_height, 200 )
        self.assertEqual( mr_duration, None )
        self.assertEqual( mr_num_frames, None )
        self.assertEqual( mr_has_audio, False )
        self.assertEqual( mr_num_words, None )
        
        ( media_result, ) = self._read( 'media_results_from_ids', ( 1, ) )
        
        ( mr_file_info_manager, mr_tags_manager, mr_locations_manager, mr_ratings_manager ) = media_result.ToTuple()
        
        ( mr_hash_id, mr_hash, mr_size, mr_mime, mr_width, mr_height, mr_duration, mr_num_frames, mr_has_audio, mr_num_words ) = mr_file_info_manager.ToTuple()
        
        mr_inbox = mr_locations_manager.inbox
        
        now = HydrusTime.GetNow()
        
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_inbox, True )
        self.assertEqual( mr_size, 5270 )
        self.assertEqual( mr_mime, HC.IMAGE_PNG )
        self.assertEqual( mr_hash, hash )
        self.assertEqual( mr_width, 200 )
        self.assertEqual( mr_height, 200 )
        self.assertEqual( mr_duration, None )
        self.assertEqual( mr_num_frames, None )
        self.assertEqual( mr_has_audio, False )
        self.assertEqual( mr_num_words, None )
        
    
    def test_mr_bones( self ):
        
        TestClientDB._clear_db()
        
        test_files = []
        
        test_files.append( 'muh_swf.swf' )
        test_files.append( 'muh_mp4.mp4' )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        for filename in test_files:
            
            TG.test_controller.SetRead( 'hash_status', ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            
            path = HydrusStaticDir.GetStaticPath( os.path.join( 'testing', filename ) )
            
            file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
            
            file_import_job.GeneratePreImportHashAndStatus()
            
            file_import_job.GenerateInfo()
            
            file_import_status = self._write( 'import_file', file_import_job )
            
        
        swf_hash_hex = 'edfef9905fdecde38e0752a5b6ab7b6df887c3968d4246adc9cffc997e168cdf'
        
        media_result = self._read( 'media_result', bytes.fromhex( swf_hash_hex ) )
        
        earliest_import_timestamp = HydrusTime.SecondiseMS( media_result.GetLocationsManager().GetTimesManager().GetImportedTimestampMS( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
        
        result = self._read( 'boned_stats' )
        
        expected_result = {
            'earliest_import_time': earliest_import_timestamp,
            'num_archive': 0,
            'num_deleted': 0,
            'num_inbox': 2,
            'size_archive': 0,
            'size_deleted': 0,
            'size_inbox': 1027308,
            'total_alternate_files': 0,
            'total_alternate_groups': 0,
            'total_duplicate_files': 0,
            'total_viewtime': (0, 0, 0, 0)
        }
        
        self.assertEqual( result, expected_result )
        
        #
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.APPLICATION_FLASH, ) ) ]
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = predicates )
        
        result = self._read( 'boned_stats', file_search_context = file_search_context )
        
        expected_result = {
            'earliest_import_time': earliest_import_timestamp,
            'num_archive': 0,
            'num_deleted': 0,
            'num_inbox': 1,
            'size_archive': 0,
            'size_deleted': 0,
            'size_inbox': 456774,
            'total_alternate_files': 0,
            'total_alternate_groups': 0,
            'total_duplicate_files': 0,
            'total_viewtime': (0, 0, 0, 0)
        }
        
        self.assertEqual( result, expected_result )
        
    
    def test_nums_pending( self ):
        
        TestClientDB._clear_db()
        
        result = self._read( 'nums_pending' )
        
        self.assertEqual( result, {} )
        
        #
        
        services = list( self._read( 'services' ) )
        
        tag_sk = HydrusData.GenerateKey()
        file_sk = HydrusData.GenerateKey()
        ipfs_sk = HydrusData.GenerateKey()
        
        services.append( ClientServices.GenerateService( tag_sk, HC.TAG_REPOSITORY, 'test tag repo' ) )
        services.append( ClientServices.GenerateService( file_sk, HC.FILE_REPOSITORY, 'test file repo' ) )
        services.append( ClientServices.GenerateService( ipfs_sk, HC.IPFS, 'test ipfs' ) )
        
        self._write( 'update_services', services )
        
        #
        
        result = self._read( 'nums_pending' )
        
        expected_result = {
            tag_sk: {
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS : 0,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS : 0,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS : 0
            },
            file_sk: {
                HC.SERVICE_INFO_NUM_PENDING_FILES: 0,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES: 0
            },
            ipfs_sk: {
                HC.SERVICE_INFO_NUM_PENDING_FILES: 0,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES: 0
            }
        }
        
        self.assertEqual( result, expected_result )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 64 ) ]
        
        tags = [ 'this', 'is', 'a:test' ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, hashes ) ) for tag in tags ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 64 ) ]
        
        tags = [ 'bad tag', 'bad' ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, hashes ) ) for tag in tags ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( tag, hashes ), reason = 'yo' ) for tag in tags ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        pairs = [
            ( 'sib tag 1a', 'sib tag 1b' ),
            ( 'sib tag 2a', 'sib tag 2b' ),
            ( 'sib tag 3a', 'sib tag 3b' ),
            ( 'sib tag 4a', 'sib tag 4b' )
        ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PEND, pair, reason = 'good sibling m8' ) for pair in pairs ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        pairs = [
            ( 'samus aran', 'princess peach' ),
            ( 'lara croft', 'princess peach' )
        ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, pair ) for pair in pairs ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, pair, reason = 'mistake' ) for pair in pairs ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        pairs = [
            ( 'par tag 1a', 'par tag 1b' ),
            ( 'par tag 2a', 'par tag 2b' ),
            ( 'par tag 3a', 'par tag 3b' )
        ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PEND, pair, reason = 'good parent m8' ) for pair in pairs ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        pairs = [
            ( 'ayanami rei', 'zelda' )
        ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_ADD, pair ) for pair in pairs ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_UPDATE_PETITION, pair, reason = 'mistake' ) for pair in pairs ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( tag_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 15 ) ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( file_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 20 ) ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PEND, hashes ) ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( ipfs_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        test_files = {
            '5d884d84813beeebd59a35e474fa3e4742d0f2b6679faa7609b245ddbbd05444' : 'muh_jpg.jpg',
            'cdc67d3b377e6e1397ffa55edc5b50f6bdf4482c7a6102c6f27fa351429d6f49' : 'muh_png.png',
            '9e7b8b5abc7cb11da32db05671ce926a2a2b701415d1b2cb77a28deea51010c3' : 'muh_apng.png'
        }
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        for ( hash, filename ) in test_files.items():
            
            TG.test_controller.SetRead( 'hash_status', ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            
            path = HydrusStaticDir.GetStaticPath( os.path.join( 'testing', filename ) )
            
            file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
            
            file_import_job.GeneratePreImportHashAndStatus()
            
            file_import_job.GenerateInfo()
            
            file_import_status = self._write( 'import_file', file_import_job )
            
        
        hashes = list( [ bytes.fromhex( hh ) for hh in test_files.keys() ] )
        
        media_results = self._read( 'media_results', hashes )
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( mr.GetFileInfoManager(), 100000 ) ) for mr in media_results ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( file_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( mr.GetFileInfoManager(), os.urandom( 16 ).hex() ) ) for mr in media_results ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( ipfs_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes, reason = 'nope' ) ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( file_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_PETITION, hashes ) ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( ipfs_sk, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        #
        
        result = self._read( 'nums_pending' )
        
        expected_result = {
            tag_sk: {
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS : 64 * 3,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS : 64 * 2,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS : 4,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS : 2,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS : 3,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS : 1
            },
            file_sk: {
                HC.SERVICE_INFO_NUM_PENDING_FILES: 15,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES: 3
            },
            ipfs_sk: {
                HC.SERVICE_INFO_NUM_PENDING_FILES: 20,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES: 3
            }
        }
        
        self.assertEqual( result, expected_result )
        
    
    def test_pending( self ):
        
        TestClientDB._clear_db()
        
        service_key = HydrusData.GenerateKey()
        
        services = self._read( 'services' )
        
        old_services = list( services )
        
        service = ClientServices.GenerateService( service_key, HC.TAG_REPOSITORY, 'new tag repo' )
        
        service._account._account_type = HydrusNetwork.AccountType.GenerateAdminAccountType( HC.TAG_REPOSITORY )
        
        services.append( service )
        
        self._write( 'update_services', services )
        
        #
        
        hashes = [ os.urandom( 32 ) for i in range( 64 ) ]
        
        tags = [ 'this', 'is', 'a:test' ]
        
        content_updates = [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, hashes ) ) for tag in tags ]
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( service_key, content_updates )
        
        self._write( 'content_updates', content_update_package )
        
        result = self._read( 'pending', service_key, ( HC.CONTENT_TYPE_MAPPINGS, ) )
        
        self.assertIsInstance( result, HydrusNetwork.ClientToServerUpdate )
        
        self.assertTrue( result.HasContent() )
        
        self.assertEqual( set( result.GetHashes() ), set( hashes ) )
        
        #
        
        TestClientDB._clear_db()
        
    
    def test_pixiv_account( self ):
        
        result = self._read( 'serialisable_simple', 'pixiv_account' )
        
        self.assertEqual( result, None )
        
        pixiv_id = 123456
        password = 'password'
        
        self._write( 'serialisable_simple', 'pixiv_account', ( pixiv_id, password ) )
        
        result = self._read( 'serialisable_simple', 'pixiv_account' )
        
        self.assertEqual( result, [ pixiv_id, password ] )
        
    
    def test_services( self ):
        
        TestClientDB._clear_db()
        
        result = self._read( 'services', ( HC.LOCAL_FILE_DOMAIN, HC.LOCAL_FILE_UPDATE_DOMAIN, HC.LOCAL_FILE_TRASH_DOMAIN, HC.HYDRUS_LOCAL_FILE_STORAGE, HC.COMBINED_LOCAL_FILE_DOMAINS, HC.LOCAL_TAG, HC.LOCAL_RATING_LIKE ) )
        
        result_service_keys = { service.GetServiceKey() for service in result }
        
        self.assertEqual( { CC.TRASH_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, CC.LOCAL_UPDATE_SERVICE_KEY, CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, CC.DEFAULT_LOCAL_DOWNLOADER_TAG_SERVICE_KEY, CC.DEFAULT_FAVOURITES_RATING_SERVICE_KEY }, result_service_keys )
        
        #
        
        result = self._read( 'service_info', CC.LOCAL_FILE_SERVICE_KEY )
        
        self.assertEqual( type( result ), dict )
        
        for ( k, v ) in list(result.items()):
            
            self.assertEqual( type( k ), int )
            self.assertEqual( type( v ), int )
            
        
        #
        
        NUM_DEFAULT_SERVICES = 13
        
        services = self._read( 'services' )
        
        self.assertEqual( len( services ), NUM_DEFAULT_SERVICES )
        
        old_services = list( services )
        
        services.append( ClientServices.GenerateService( HydrusData.GenerateKey(), HC.TAG_REPOSITORY, 'new service' ) )
        
        self._write( 'update_services', services )
        
        services = self._read( 'services' )
        
        self.assertEqual( len( services ), NUM_DEFAULT_SERVICES + 1 )
        
        self._write( 'update_services', old_services )
        
        services = self._read( 'services' )
        
        self.assertEqual( len( services ), NUM_DEFAULT_SERVICES )
        
    
    def test_shortcuts( self ):
        
        num_default = len( ClientDefaults.GetDefaultShortcuts() )
        
        result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
        
        self.assertEqual( len( result ), num_default )
        
        #
        
        for ( i, shortcuts ) in enumerate( ClientDefaults.GetDefaultShortcuts() ):
            
            name = 'shortcuts ' + str( i )
            
            shortcuts.SetName( name )
            
            self._write( 'serialisable', shortcuts )
            
            result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
            
            self.assertEqual( len( result ), num_default + 1 )
            
            result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET, name )
            
            for ( shortcut, command ) in shortcuts:
                
                self.assertEqual( tuple( result.GetCommand( shortcut )._data ), tuple( command._data ) )
                
            
            #
            
            self._write( 'delete_serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET, name )
            
            result = self._read( 'serialisable_named', HydrusSerialisable.SERIALISABLE_TYPE_SHORTCUT_SET )
            
            self.assertEqual( len( result ), num_default )
            
        
    
