import collections
import collections.abc
import os
import random
import time
import typing
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusTagArchive
from hydrus.core import HydrusData
from hydrus.core import HydrusTags

from hydrus.test import TestController

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client import ClientMigration
from hydrus.client import ClientServices
from hydrus.client.db import ClientDB
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.media import ClientMediaResultCache
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags

from hydrus.test import TestGlobals as TG

current_tag_pool = [ 'blonde hair', 'blue eyes', 'bodysuit', 'character:samus aran', 'series:metroid', 'studio:nintendo' ]
pending_tag_pool = [ 'favourites', 'kino', 'brown shirt', 'huge knees' ]
deleted_tag_pool = [ 'trash', 'ugly', 'character:smaus aran', 'red hair' ]

to_be_pended_tag_pool = [ 'clothing:high heels', 'firearm', 'puffy armpit' ]

current_parents_pool = []

current_parents_pool.append( ( 'character:princess peach', 'series:super mario bros' ) )
current_parents_pool.append( ( 'character:princess peach', 'gender:female' ) )
current_parents_pool.append( ( 'mario_(mario)', 'series:super mario bros' ) )
current_parents_pool.append( ( 'meta:explicit', 'nsfw' ) )
current_parents_pool.append( ( 'bepis', 'genidalia' ) )
current_parents_pool.append( ( 'bagina', 'genidalia' ) )

pending_parents_pool = []

pending_parents_pool.append( ( 'character:princess daisy', 'series:super mario bros' ) )
pending_parents_pool.append( ( 'character:princess daisy', 'gender:female' ) )
pending_parents_pool.append( ( 'mario_(mario)', 'series:super mario bros' ) )
pending_parents_pool.append( ( 'bepis', 'genidalia' ) )
pending_parents_pool.append( ( 'bagina', 'genidalia' ) )

to_be_pended_parents_pool = []

to_be_pended_parents_pool.append( ( 'pend:parent a', 'pend:parent b' ) )
to_be_pended_parents_pool.append( ( 'parent c', 'parent d' ) )

deleted_parents_pool = []

deleted_parents_pool.append( ( 'male', 'human' ) )
deleted_parents_pool.append( ( 'table', 'general:furniture' ) )
deleted_parents_pool.append( ( 'character:iron man', 'studio:dc' ) )

current_siblings_pool = []

current_siblings_pool.append( ( 'lara_croft', 'character:lara croft' ) )
current_siblings_pool.append( ( 'lara croft', 'character:lara croft' ) )
current_siblings_pool.append( ( 'series:tomb raider (series)', 'series:tomb raider' ) )
current_siblings_pool.append( ( 'general:lamp', 'lamp' ) )
current_siblings_pool.append( ( 'bog', 'bepis' ) )
current_siblings_pool.append( ( 'buggy', 'bagina' ) )

pending_siblings_pool = []

pending_siblings_pool.append( ( 'horse', 'species:horse' ) )
pending_siblings_pool.append( ( 'equine', 'species:equine' ) )
pending_siblings_pool.append( ( 'dog', 'species:dog' ) )
pending_siblings_pool.append( ( 'canine', 'species:canine' ) )
pending_siblings_pool.append( ( 'eguine', 'equine' ) )

to_be_pended_siblings_pool = []

to_be_pended_siblings_pool.append( ( 'pend:sibling a', 'pend:sibling b' ) )
to_be_pended_siblings_pool.append( ( 'sibling c', 'sibling d' ) )

deleted_siblings_pool = []

deleted_siblings_pool.append( ( 'male', 'male:male' ) )
deleted_siblings_pool.append( ( 'table', 'general:table' ) )
deleted_siblings_pool.append( ( 'shadow', 'character:shadow the hedgehog' ) )

pair_types_to_pools = {}

pair_types_to_pools[ HC.CONTENT_TYPE_TAG_PARENTS ] = ( current_parents_pool, pending_parents_pool, to_be_pended_parents_pool, deleted_parents_pool )
pair_types_to_pools[ HC.CONTENT_TYPE_TAG_SIBLINGS ] = ( current_siblings_pool, pending_siblings_pool, to_be_pended_siblings_pool, deleted_siblings_pool )

count_filter_pairs = {}

count_filter_pairs[ HC.CONTENT_TYPE_TAG_SIBLINGS ] = [
    ( 'has_count_a_ideal_no', 'no_count_b' ),
    ( 'no_count_c_ideal_yes', 'has_count_d' ),
    ( 'no_count_e_ideal_yes', 'has_count_f' ),
    ( 'has_count_g_ideal_yes', 'has_count_h' ),
    ( 'has_count_aa_ideal_yes', 'no_count_bb_ideal_yes' ),
    ( 'no_count_bb_ideal_yes', 'has_count_cc' ),
    ( 'has_count_dd_ideal_no', 'has_count_ee_ideal_no' ),
    ( 'has_count_ee_ideal_no', 'no_count_ff' ),
]

count_filter_pairs[ HC.CONTENT_TYPE_TAG_PARENTS ] = [
    ( 'has_count_a', 'no_count_b' ),
    ( 'no_count_c', 'has_count_d' ),
    ( 'no_count_e', 'has_count_f' ),
    ( 'has_count_g', 'has_count_h' )
]

class TestMigration( unittest.TestCase ):
    
    _db: typing.Any = None
    
    @classmethod
    def _clear_db( cls ):
        
        cls._delete_db()
        
        # class variable
        cls._db = ClientDB.DB( TG.test_controller, TestController.DB_DIR, 'client' )
        
    
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
        
    
    @classmethod
    def setUpClass( cls ):
        
        cls._db = ClientDB.DB( TG.test_controller, TestController.DB_DIR, 'client' )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._delete_db()
        
    
    def pub( self, *args, **kwargs ): pass
    def sub( self, *args, **kwargs ): pass
    
    def Read( self, action, *args, **kwargs ): return TestMigration._db.Read( action, *args, **kwargs )
    def WriteSynchronous( self, action, *args, **kwargs ): return TestMigration._db.Write( action, True, *args, **kwargs )
    
    def _set_up_services( self ):
        
        self._test_tag_repo_service_keys = {}
        
        services = self.Read( 'services' )
        
        for i in range( 20 ):
            
            service_key = HydrusData.GenerateKey()
            
            services.append( ClientServices.GenerateService( service_key, HC.TAG_REPOSITORY, 'test repo {}'.format( i ) ) )
            
            self._test_tag_repo_service_keys[ i ] = service_key
            
        
        self.WriteSynchronous( 'update_services', services )
        
        self.services_manager = ClientServices.ServicesManager( self )
        
    
    def _do_fake_imports( self ):
        
        self._md5_to_sha256 = {}
        self._sha256_to_md5 = {}
        self._sha256_to_sha1 = {}
        
        self._my_files_sha256 = set()
        
        self._hashes_to_current_tags = {}
        self._hashes_to_pending_tags = {}
        self._hashes_to_deleted_tags = {}
        
        ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = ( 65535, HC.IMAGE_JPEG, 640, 480, None, None, False, None )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        for i in range( 100 ):
            
            hash = HydrusData.GenerateKey()
            md5 = os.urandom( 16 )
            sha1 = os.urandom( 20 )
            sha512 = os.urandom( 64 )
            
            self._md5_to_sha256[ md5 ] = hash
            self._sha256_to_md5[ hash ] = md5
            self._sha256_to_sha1[ hash ] = sha1
            
            self._hashes_to_current_tags[ hash ] = set( random.sample( current_tag_pool, 3 ) )
            self._hashes_to_pending_tags[ hash ] = set( random.sample( pending_tag_pool, 3 ) )
            self._hashes_to_deleted_tags[ hash ] = set( random.sample( deleted_tag_pool, 3 ) )
            
            if i < 50:
                
                fake_file_import_job = ClientImportFiles.FileImportJob( 'fake path', file_import_options )
                
                fake_file_import_job._pre_import_file_status = ClientImportFiles.FileImportStatus( CC.STATUS_UNKNOWN, hash )
                fake_file_import_job._file_info = ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words )
                fake_file_import_job._extra_hashes = ( md5, sha1, sha512 )
                fake_file_import_job._perceptual_hashes = [ os.urandom( 8 ) ]
                
                self.WriteSynchronous( 'import_file', fake_file_import_job )
                
                self._my_files_sha256.add( hash )
                
            
        
    
    def _add_mappings_to_services( self ):
        
        content_updates = []
        
        for ( hash, tags ) in self._hashes_to_current_tags.items():
            
            for tag in tags:
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( hash, ) ) ) )
                
            
        
        for ( hash, tags ) in self._hashes_to_deleted_tags.items():
            
            for tag in tags:
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, ( hash, ) ) ) )
                
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_updates )
        
        self.WriteSynchronous( 'content_updates', content_update_package )
        
        content_updates = []
        
        for ( hash, tags ) in self._hashes_to_current_tags.items():
            
            for tag in tags:
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( hash, ) ) ) )
                
            
        
        for ( hash, tags ) in self._hashes_to_pending_tags.items():
            
            for tag in tags:
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, ( hash, ) ) ) )
                
            
        
        for ( hash, tags ) in self._hashes_to_deleted_tags.items():
            
            for tag in tags:
                
                content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, ( hash, ) ) ) )
                
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        for service_key in self._test_tag_repo_service_keys.values():
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        self.WriteSynchronous( 'content_updates', content_update_package )
        
    
    def _test_mappings_list_to_list( self ):
        
        data = list( self._hashes_to_current_tags.items() )
        
        self.assertTrue( len( data ) > 0 )
        
        source = ClientMigration.MigrationSourceList( self, data )
        destination = ClientMigration.MigrationDestinationListMappings( self )
        
        job = ClientMigration.MigrationJob( self, 'test', source, destination )
        
        job.Run()
        
        self.assertEqual( destination.GetDataReceived(), data )
        
    
    def _test_mappings_hta_to_list( self ):
        
        def run_test( source, expected_data ):
            
            destination = ClientMigration.MigrationDestinationListMappings( self )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            self.assertEqual( dict( destination.GetDataReceived() ), dict( expected_data ) )
            
        
        md5_hta_path = os.path.join( TestController.DB_DIR, 'md5hta.db' )
        sha256_hta_path = os.path.join( TestController.DB_DIR, 'sha256hta.db' )
        
        md5_hta = HydrusTagArchive.HydrusTagArchive( md5_hta_path )
        sha256_hta = HydrusTagArchive.HydrusTagArchive( sha256_hta_path )
        
        md5_hta.SetHashType( HydrusTagArchive.HASH_TYPE_MD5 )
        sha256_hta.SetHashType( HydrusTagArchive.HASH_TYPE_SHA256 )
        
        md5_hta.BeginBigJob()
        sha256_hta.BeginBigJob()
        
        for ( hash, tags ) in self._hashes_to_current_tags.items():
            
            md5 = self._sha256_to_md5[ hash ]
            
            md5_hta.AddMappings( md5, tags )
            sha256_hta.AddMappings( hash, tags )
            
        
        md5_hta.CommitBigJob()
        sha256_hta.CommitBigJob()
        
        md5_hta.Optimise()
        sha256_hta.Optimise()
        
        md5_hta.Close()
        sha256_hta.Close()
        
        del md5_hta
        del sha256_hta
        
        #
        
        # test file filter
        
        tag_filter = HydrusTags.TagFilter()
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'md5', None, tag_filter )
        
        expected_data = [ ( self._sha256_to_md5[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter )
        
        expected_data = list( self._hashes_to_current_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), 'md5', None, tag_filter )
        
        expected_data = [ ( self._sha256_to_md5[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), 'sha256', None, tag_filter )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        run_test( source, expected_data )
        
        # not all hashes, since hash type lookup only available for imported files
        hashes = random.sample( list( self._my_files_sha256 ), 25 )
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'md5', hashes, tag_filter )
        
        expected_data = [ ( self._sha256_to_md5[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', hashes, tag_filter )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        run_test( source, expected_data )
        
        # test desired hash type
        
        # not all hashes, since hash type lookup only available for imported files
        expected_data = [ ( self._sha256_to_sha1[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha1', None, tag_filter )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha1', None, tag_filter )
        
        run_test( source, expected_data )
        
        # do a test with specific hashes, so md5->sha1 does interim sha256 conversion
        # not all hashes, since hash type lookup only available for imported files
        hashes = random.sample( list( self._my_files_sha256 ), 25 )
        
        expected_data = [ ( self._sha256_to_sha1[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha1', hashes, tag_filter )
        
        run_test( source, expected_data )
        
        # tag filter
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_WHITELIST )
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'md5', None, tag_filter )
        
        expected_data = [ ( self._sha256_to_md5[ hash ], tag_filter.Filter( tags ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        expected_data = [ ( hash, tags ) for ( hash, tags ) in expected_data if len( tags ) > 0 ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter )
        
        expected_data = [ ( hash, tag_filter.Filter( tags ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        expected_data = [ ( hash, tags ) for ( hash, tags ) in expected_data if len( tags ) > 0 ]
        
        run_test( source, expected_data )
        
        #
        
        os.remove( md5_hta_path )
        os.remove( sha256_hta_path )
        
    
    def _test_mappings_list_to_hta( self ):
        
        def run_test( source, destination_path, desired_hash_type, expected_data ):
            
            destination = ClientMigration.MigrationDestinationHTA( self, destination_path, desired_hash_type )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            hta = HydrusTagArchive.HydrusTagArchive( destination_path )
            
            result = list( hta.IterateMappings() )
            
            self.assertEqual( dict( result ), dict( expected_data ) )
            
            hta.Close()
            
        
        md5_hta_path = os.path.join( TestController.DB_DIR, 'md5hta.db' )
        sha256_hta_path = os.path.join( TestController.DB_DIR, 'sha256hta.db' )
        
        #
        
        md5_data = [ ( self._sha256_to_md5[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        sha256_data = list( self._hashes_to_current_tags.items() )
        
        md5_source = ClientMigration.MigrationSourceList( self, md5_data )
        sha256_source = ClientMigration.MigrationSourceList( self, sha256_data )
        
        run_test( md5_source, md5_hta_path, 'md5', md5_data )
        run_test( sha256_source, sha256_hta_path, 'sha256', sha256_data )
        
        #
        
        os.remove( md5_hta_path )
        os.remove( sha256_hta_path )
        
    
    def _test_mappings_service_to_list( self ):
        
        def run_test( source, expected_data ):
            
            destination = ClientMigration.MigrationDestinationListMappings( self )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            self.assertEqual( dict( destination.GetDataReceived() ), dict( expected_data ) )
            
        
        # test file filter
        
        tag_repo_service_key = self._test_tag_repo_service_keys[0]
        
        tag_filter = HydrusTags.TagFilter()
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = list( self._hashes_to_current_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = list( self._hashes_to_current_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        run_test( source, expected_data )
        
        # not all hashes, since hash type lookup only available for imported files
        hashes = random.sample( list( self._my_files_sha256 ), 25 )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', hashes, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', hashes, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        run_test( source, expected_data )
        
        # test desired hash type
        
        # not all hashes, since hash type lookup only available for imported files
        expected_data = [ ( self._sha256_to_sha1[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha1', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha1', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        run_test( source, expected_data )
        
        # tag filter
        
        tag_filter = HydrusTags.TagFilter()
        
        tag_filter.SetRule( '', HC.FILTER_WHITELIST )
        tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tag_filter.Filter( tags ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        expected_data = [ ( hash, tags ) for ( hash, tags ) in expected_data if len( tags ) > 0 ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tag_filter.Filter( tags ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        expected_data = [ ( hash, tags ) for ( hash, tags ) in expected_data if len( tags ) > 0 ]
        
        run_test( source, expected_data )
        
        # test statuses
        
        tag_filter = HydrusTags.TagFilter()
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_DELETED, ) )
        
        expected_data = list( self._hashes_to_deleted_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_DELETED, ) )
        
        expected_data = list( self._hashes_to_deleted_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_FILE_SERVICE_KEY ), 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) )
        
        expected_data = collections.defaultdict( set )
        
        for ( hash, tags ) in self._hashes_to_current_tags.items():
            
            expected_data[ hash ].update( tags )
            
        
        for ( hash, tags ) in self._hashes_to_pending_tags.items():
            
            expected_data[ hash ].update( tags )
            
        
        expected_data = list( expected_data.items() )
        
        run_test( source, expected_data )
        
    
    def _test_mappings_list_to_service( self ):
        
        def run_test( source, tag_service_key, content_action, expected_data ):
            
            destination = ClientMigration.MigrationDestinationTagServiceMappings( self, tag_service_key, content_action )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            self._db.modules_media_results._weakref_media_result_cache = ClientMediaResultCache.MediaResultCache()
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in self.Read( 'media_results', list( self._hashes_to_current_tags.keys() ) ) }
            
            for ( hash, tags ) in expected_data:
                
                media_result = hashes_to_media_results[ hash ]
                
                t_m = media_result.GetTagsManager()
                
                if content_action == HC.CONTENT_UPDATE_ADD:
                    
                    current_tags = t_m.GetCurrent( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                    
                    for tag in tags:
                        
                        self.assertIn( tag, current_tags )
                        
                    
                elif content_action == HC.CONTENT_UPDATE_DELETE:
                    
                    current_tags = t_m.GetCurrent( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                    deleted_tags = t_m.GetDeleted( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                    
                    for tag in tags:
                        
                        self.assertNotIn( tag, current_tags )
                        self.assertIn( tag, deleted_tags )
                        
                    
                elif content_action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                    
                    deleted_tags = t_m.GetDeleted( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                    
                    for tag in tags:
                        
                        self.assertNotIn( tag, deleted_tags )
                        
                    
                elif content_action == HC.CONTENT_UPDATE_PEND:
                    
                    pending_tags = t_m.GetPending( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                    
                    for tag in tags:
                        
                        self.assertIn( tag, pending_tags )
                        
                    
                elif content_action == HC.CONTENT_UPDATE_PETITION:
                    
                    petitioned_tags = t_m.GetPetitioned( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                    
                    for tag in tags:
                        
                        self.assertIn( tag, petitioned_tags )
                        
                    
                
            
        
        #
        
        # local add
        
        data = [ ( hash, set( random.sample( to_be_pended_tag_pool, 2 ) ) ) for hash in self._hashes_to_current_tags.keys() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_UPDATE_ADD, data )
        
        # local delete
        
        data = [ ( hash, set( random.sample( list( tags ), 2 ) ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_UPDATE_DELETE, data )
        
        # local clear deletion record
        
        data = [ ( hash, set( random.sample( list( tags ), 2 ) ) ) for ( hash, tags ) in self._hashes_to_deleted_tags.items() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, data )
        
        # tag repo pend
        
        data = [ ( hash, set( random.sample( to_be_pended_tag_pool, 2 ) ) ) for hash in self._hashes_to_current_tags.keys() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, self._test_tag_repo_service_keys[1], HC.CONTENT_UPDATE_PEND, data )
        
        # tag repo petition
        
        data = [ ( hash, set( random.sample( list( tags ), 2 ) ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, self._test_tag_repo_service_keys[1], HC.CONTENT_UPDATE_PETITION, data )
        
    
    def _add_pairs_to_services( self, content_type ):
        
        ( current, pending, to_be_pended, deleted ) = pair_types_to_pools[ content_type ]
        
        content_updates = []
        
        for pair in current:
            
            content_updates.append( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_ADD, pair ) )
            
        
        for pair in deleted:
            
            content_updates.append( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_DELETE, pair ) )
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_updates )
        
        self.WriteSynchronous( 'content_updates', content_update_package )
        
        content_updates = []
        
        for pair in current:
            
            content_updates.append( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_ADD, pair ) )
            
        
        for pair in pending:
            
            content_updates.append( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_PEND, pair ) )
            
        
        for pair in deleted:
            
            content_updates.append( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_DELETE, pair ) )
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        for service_key in self._test_tag_repo_service_keys.values():
            
            content_update_package.AddContentUpdates( service_key, content_updates )
            
        
        self.WriteSynchronous( 'content_updates', content_update_package )
        
    
    def _test_pairs_list_to_list( self, content_type ):
        
        ( current, pending, to_be_pended, deleted ) = pair_types_to_pools[ content_type ]
        
        data = list( current )
        
        self.assertTrue( len( data ) > 0 )
        
        source = ClientMigration.MigrationSourceList( self, data )
        destination = ClientMigration.MigrationDestinationListPairs( self )
        
        job = ClientMigration.MigrationJob( self, 'test', source, destination )
        
        job.Run()
        
        self.assertEqual( destination.GetDataReceived(), data )
        
    
    def _test_pairs_htpa_to_list( self, content_type ):
        
        def run_test( source, expected_data ):
            
            destination = ClientMigration.MigrationDestinationListPairs( self )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            self.assertEqual( set( destination.GetDataReceived() ), set( expected_data ) )
            
        
        ( current, pending, to_be_pended, deleted ) = pair_types_to_pools[ content_type ]
        
        htpa_path = os.path.join( TestController.DB_DIR, 'htpa.db' )
        
        htpa = HydrusTagArchive.HydrusTagPairArchive( htpa_path )
        
        if content_type == HC.CONTENT_TYPE_TAG_PARENTS:
            
            htpa.SetPairType( HydrusTagArchive.TAG_PAIR_TYPE_PARENTS )
            
        elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
            
            htpa.SetPairType( HydrusTagArchive.TAG_PAIR_TYPE_SIBLINGS )
            
        
        htpa.BeginBigJob()
        
        htpa.AddPairs( current )
        
        htpa.CommitBigJob()
        
        htpa.Optimise()
        
        htpa.Close()
        
        del htpa
        
        #
        
        # test tag filter, left, right, both
        
        free_filter = HydrusTags.TagFilter()
        
        namespace_filter = HydrusTags.TagFilter()
        
        namespace_filter.SetRule( ':', HC.FILTER_WHITELIST )
        namespace_filter.SetRule( '', HC.FILTER_BLACKLIST )
        
        test_filters = []
        
        test_filters.append( ( free_filter, free_filter ) )
        test_filters.append( ( namespace_filter, free_filter ) )
        test_filters.append( ( free_filter, namespace_filter ) )
        test_filters.append( ( namespace_filter, namespace_filter ) )
        
        left_side_needs_count = False
        right_side_needs_count = False
        either_side_needs_count = False
        needs_count_service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
        
        for ( left_tag_filter, right_tag_filter ) in test_filters:
            
            source = ClientMigration.MigrationSourceHTPA( self, htpa_path, content_type, left_tag_filter, right_tag_filter, left_side_needs_count, right_side_needs_count, either_side_needs_count, needs_count_service_key )
            
            expected_data = [ ( left_tag, right_tag ) for ( left_tag, right_tag ) in current if left_tag_filter.TagOK( left_tag ) and right_tag_filter.TagOK( right_tag ) ]
            
            run_test( source, expected_data )
            
        
        #
        
        os.remove( htpa_path )
        
    
    def _test_pairs_list_to_htpa( self, content_type ):
        
        def run_test( source, destination_path, content_type, expected_data ):
            
            destination = ClientMigration.MigrationDestinationHTPA( self, destination_path, content_type )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            hta = HydrusTagArchive.HydrusTagPairArchive( destination_path )
            
            result = list( hta.IteratePairs() )
            
            self.assertEqual( set( result ), set( expected_data ) )
            
            hta.Close()
            
        
        ( current, pending, to_be_pended, deleted ) = pair_types_to_pools[ content_type ]
        
        htpa_path = os.path.join( TestController.DB_DIR, 'htpa.db' )
        
        #
        
        source = ClientMigration.MigrationSourceList( self, current )
        
        run_test( source, htpa_path, content_type, list( current ) )
        
        #
        
        os.remove( htpa_path )
        
    
    def _test_pairs_service_to_list( self, content_type ):
        
        def run_test( source, expected_data ):
            
            destination = ClientMigration.MigrationDestinationListPairs( self )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            self.assertEqual( set( destination.GetDataReceived() ), set( expected_data ) )
            
        
        ( current, pending, to_be_pended, deleted ) = pair_types_to_pools[ content_type ]
        
        # test filters and content statuses
        
        tag_repo_service_key = self._test_tag_repo_service_keys[10]
        
        content_source_tests = []
        
        content_source_tests.append( ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ( current, ), ( HC.CONTENT_STATUS_CURRENT, ) ) )
        content_source_tests.append( ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ( deleted, ), ( HC.CONTENT_STATUS_DELETED, ) ) )
        content_source_tests.append( ( tag_repo_service_key, ( current, ), ( HC.CONTENT_STATUS_CURRENT, ) ) )
        content_source_tests.append( ( tag_repo_service_key, ( current, pending ), ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) ) )
        content_source_tests.append( ( tag_repo_service_key, ( deleted, ), ( HC.CONTENT_STATUS_DELETED, ) ) )
        
        free_filter = HydrusTags.TagFilter()
        
        namespace_filter = HydrusTags.TagFilter()
        
        namespace_filter.SetRule( ':', HC.FILTER_WHITELIST )
        namespace_filter.SetRule( '', HC.FILTER_BLACKLIST )
        
        test_filters = []
        
        test_filters.append( ( free_filter, free_filter ) )
        test_filters.append( ( namespace_filter, free_filter ) )
        test_filters.append( ( free_filter, namespace_filter ) )
        test_filters.append( ( namespace_filter, namespace_filter ) )
        
        left_side_needs_count = False
        right_side_needs_count = False
        either_side_needs_count = False
        needs_count_service_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
        
        for ( left_tag_filter, right_tag_filter ) in test_filters:
            
            for ( service_key, content_lists, content_statuses ) in content_source_tests:
                
                source = ClientMigration.MigrationSourceTagServicePairs( self, service_key, content_type, left_tag_filter, right_tag_filter, content_statuses, left_side_needs_count, right_side_needs_count, either_side_needs_count, needs_count_service_key )
                
                expected_data = set()
                
                for content_list in content_lists:
                    
                    expected_data.update( ( ( left_tag, right_tag ) for ( left_tag, right_tag ) in content_list if left_tag_filter.TagOK( left_tag ) and right_tag_filter.TagOK( right_tag ) ) )
                    
                
                run_test( source, expected_data )
                
            
        
    
    def _test_pairs_list_to_service( self, content_type ):
        
        def run_test( source, tag_service_key, content_action, expected_data ):
            
            destination = ClientMigration.MigrationDestinationTagServicePairs( self, tag_service_key, content_action, content_type )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            if content_type == HC.CONTENT_TYPE_TAG_PARENTS:
                
                statuses_to_pairs = self.Read( 'tag_parents', tag_service_key )
                
            elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
                
                statuses_to_pairs = self.Read( 'tag_siblings', tag_service_key )
                
            
            if content_action == HC.CONTENT_UPDATE_ADD:
                
                should_be_in = set( statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ] )
                should_not_be_in = set( statuses_to_pairs[ HC.CONTENT_STATUS_DELETED ] )
                
            elif content_action == HC.CONTENT_UPDATE_DELETE:
                
                should_be_in = set( statuses_to_pairs[ HC.CONTENT_STATUS_DELETED ] )
                should_not_be_in = set( statuses_to_pairs[ HC.CONTENT_STATUS_CURRENT ] )
                
            elif content_action == HC.CONTENT_UPDATE_PEND:
                
                should_be_in = set( statuses_to_pairs[ HC.CONTENT_STATUS_PENDING ] )
                should_not_be_in = set()
                
            elif content_action == HC.CONTENT_UPDATE_PETITION:
                
                should_be_in = set( statuses_to_pairs[ HC.CONTENT_STATUS_PETITIONED ] )
                should_not_be_in = set()
                
            
            for pair in expected_data:
                
                self.assertIn( pair, should_be_in )
                self.assertNotIn( pair, should_not_be_in )
                
            
        
        #
        
        tag_repo_service_key = self._test_tag_repo_service_keys[11]
        
        ( current, pending, to_be_pended, deleted ) = pair_types_to_pools[ content_type ]
        
        test_rows = []
        
        test_rows.append( ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, to_be_pended, HC.CONTENT_UPDATE_ADD ) )
        test_rows.append( ( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, random.sample( current, 3 ), HC.CONTENT_UPDATE_DELETE ) )
        test_rows.append( ( tag_repo_service_key, to_be_pended, HC.CONTENT_UPDATE_PEND ) )
        test_rows.append( ( tag_repo_service_key, random.sample( current, 3 ), HC.CONTENT_UPDATE_PETITION ) )
        
        for ( service_key, data, action ) in test_rows:
            
            source = ClientMigration.MigrationSourceList( self, data )
            
            run_test( source, service_key, action, data )
            
        
    
    def _add_count_filter_pairs_to_services( self, content_type ):
        
        content_updates = []
        
        for pair in count_filter_pairs[ content_type ]:
            
            content_updates.append( ClientContentUpdates.ContentUpdate( content_type, HC.CONTENT_UPDATE_ADD, pair ) )
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_updates )
        
        self.WriteSynchronous( 'content_updates', content_update_package )
        
    
    def _add_count_filter_mappings_to_services( self, content_type ):
        
        content_updates = []
        
        for ( a, b ) in count_filter_pairs[ content_type ]:
            
            for tag in ( a, b ):
                
                if 'has_count' in tag:
                    
                    content_updates.append( ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( os.urandom( 32 ), ) ) ) )
                    
                
            
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_updates )
        
        self.WriteSynchronous( 'content_updates', content_update_package )
        
    
    def _test_pairs_htpa_to_list_count_filter( self, content_type ):
        
        def run_test( source, expected_data ):
            
            destination = ClientMigration.MigrationDestinationListPairs( self )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            self.assertEqual( set( destination.GetDataReceived() ), set( expected_data ) )
            
        
        htpa_path = os.path.join( TestController.DB_DIR, 'htpa.db' )
        
        htpa = HydrusTagArchive.HydrusTagPairArchive( htpa_path )
        
        if content_type == HC.CONTENT_TYPE_TAG_PARENTS:
            
            htpa.SetPairType( HydrusTagArchive.TAG_PAIR_TYPE_PARENTS )
            
        elif content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
            
            htpa.SetPairType( HydrusTagArchive.TAG_PAIR_TYPE_SIBLINGS )
            
        
        htpa.BeginBigJob()
        
        htpa.AddPairs( count_filter_pairs[ content_type ] )
        
        htpa.CommitBigJob()
        
        htpa.Optimise()
        
        htpa.Close()
        
        del htpa
        
        #
        
        repo_service_key = list( self._test_tag_repo_service_keys.values() )[0]
        
        # test
        
        left_tag_filter = HydrusTags.TagFilter()
        right_tag_filter = HydrusTags.TagFilter()
        
        either_side_needs_count = False
        
        for left_side_needs_count in ( False, True ):
            
            for right_side_needs_count in ( False, True ):
                
                for needs_count_service_key in ( repo_service_key, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ):
                    
                    source = ClientMigration.MigrationSourceHTPA( self, htpa_path, content_type, left_tag_filter, right_tag_filter, left_side_needs_count, right_side_needs_count, either_side_needs_count, needs_count_service_key )
                    
                    if needs_count_service_key == repo_service_key:
                        
                        expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if not left_side_needs_count and not right_side_needs_count ]
                        
                    else:
                        
                        if content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
                            
                            expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if ( not left_side_needs_count or 'has_count' in a ) and ( not right_side_needs_count or 'ideal_yes' in a ) ]
                            
                        else:
                            
                            expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if ( not left_side_needs_count or 'has_count' in a ) and ( not right_side_needs_count or 'has_count' in b ) ]
                            
                        
                    
                    run_test( source, expected_data )
                    
                
            
        
        left_side_needs_count = False
        right_side_needs_count = False
        
        for either_side_needs_count in ( False, True ):
            
            for needs_count_service_key in ( repo_service_key, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ):
                
                source = ClientMigration.MigrationSourceHTPA( self, htpa_path, content_type, left_tag_filter, right_tag_filter, left_side_needs_count, right_side_needs_count, either_side_needs_count, needs_count_service_key )
                
                if needs_count_service_key == repo_service_key:
                    
                    expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if not either_side_needs_count ]
                    
                else:
                    
                    if content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
                        
                        expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if not either_side_needs_count or 'has_count' in a or 'ideal_yes' in a ]
                        
                    else:
                        
                        expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if not either_side_needs_count or 'has_count' in a or 'has_count' in b ]
                        
                    
                
                run_test( source, expected_data )
                
            
        
        #
        
        os.remove( htpa_path )
        
    
    def _test_pairs_service_to_list_count_filter( self, content_type ):
        
        def run_test( source, expected_data ):
            
            destination = ClientMigration.MigrationDestinationListPairs( self )
            
            job = ClientMigration.MigrationJob( self, 'test', source, destination )
            
            job.Run()
            
            self.assertEqual( set( destination.GetDataReceived() ), set( expected_data ) )
            
        
        # test filters and content statuses
        
        repo_service_key = list( self._test_tag_repo_service_keys.values() )[0]
        
        # test
        
        content_statuses = ( HC.CONTENT_STATUS_CURRENT, )
        
        left_tag_filter = HydrusTags.TagFilter()
        right_tag_filter = HydrusTags.TagFilter()
        
        either_side_needs_count = False
        
        for left_side_needs_count in ( False, True ):
            
            for right_side_needs_count in ( False, True ):
                
                for needs_count_service_key in ( repo_service_key, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ):
                    
                    source = ClientMigration.MigrationSourceTagServicePairs( self, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_type, left_tag_filter, right_tag_filter, content_statuses, left_side_needs_count, right_side_needs_count, either_side_needs_count, needs_count_service_key )
                    
                    if needs_count_service_key == repo_service_key:
                        
                        expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if not left_side_needs_count and not right_side_needs_count ]
                        
                    else:
                        
                        if content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
                            
                            expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if ( not left_side_needs_count or 'has_count' in a ) and ( not right_side_needs_count or 'ideal_yes' in a ) ]
                            
                        else:
                            
                            expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if ( not left_side_needs_count or 'has_count' in a ) and ( not right_side_needs_count or 'has_count' in b ) ]
                            
                        
                    
                    run_test( source, expected_data )
                    
                
            
        
        left_side_needs_count = False
        right_side_needs_count = False
        
        for either_side_needs_count in ( False, True ):
            
            for needs_count_service_key in ( repo_service_key, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ):
                
                source = ClientMigration.MigrationSourceTagServicePairs( self, CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, content_type, left_tag_filter, right_tag_filter, content_statuses, left_side_needs_count, right_side_needs_count, either_side_needs_count, needs_count_service_key )
                
                if needs_count_service_key == repo_service_key:
                    
                    expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if not either_side_needs_count ]
                    
                else:
                    
                    if content_type == HC.CONTENT_TYPE_TAG_SIBLINGS:
                        
                        expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if not either_side_needs_count or 'has_count' in a or 'ideal_yes' in a ]
                        
                    else:
                        
                        expected_data = [ ( a, b ) for ( a, b ) in count_filter_pairs[ content_type ] if not either_side_needs_count or 'has_count' in a or 'has_count' in b ]
                        
                    
                
                run_test( source, expected_data )
                
            
        
    
    def test_migration_mappings( self ):
        
        # mappings
        
        self._clear_db()
        
        self._set_up_services()
        self._do_fake_imports()
        self._add_mappings_to_services()
        
        self._test_mappings_list_to_list()
        self._test_mappings_hta_to_list()
        self._test_mappings_list_to_hta()
        self._test_mappings_service_to_list()
        self._test_mappings_list_to_service()
        
    
    def test_migration_parents( self ):
        
        self._clear_db()
        
        self._set_up_services()
        
        self._add_pairs_to_services( HC.CONTENT_TYPE_TAG_PARENTS )
        self._test_pairs_list_to_list( HC.CONTENT_TYPE_TAG_PARENTS )
        self._test_pairs_htpa_to_list( HC.CONTENT_TYPE_TAG_PARENTS )
        self._test_pairs_list_to_htpa( HC.CONTENT_TYPE_TAG_PARENTS )
        self._test_pairs_service_to_list( HC.CONTENT_TYPE_TAG_PARENTS )
        self._test_pairs_list_to_service( HC.CONTENT_TYPE_TAG_PARENTS )
        
    
    def test_migration_parents_count_filter( self ):
        
        self._clear_db()
        
        self._set_up_services()
        
        self._add_count_filter_pairs_to_services( HC.CONTENT_TYPE_TAG_PARENTS )
        self._add_count_filter_mappings_to_services( HC.CONTENT_TYPE_TAG_PARENTS )
        self._test_pairs_htpa_to_list_count_filter( HC.CONTENT_TYPE_TAG_PARENTS )
        self._test_pairs_service_to_list_count_filter( HC.CONTENT_TYPE_TAG_PARENTS )
        
    
    def test_migration_siblings( self ):
        
        self._clear_db()
        
        self._set_up_services()
        
        self._add_pairs_to_services( HC.CONTENT_TYPE_TAG_SIBLINGS )
        self._test_pairs_list_to_list( HC.CONTENT_TYPE_TAG_SIBLINGS )
        self._test_pairs_htpa_to_list( HC.CONTENT_TYPE_TAG_SIBLINGS )
        self._test_pairs_list_to_htpa( HC.CONTENT_TYPE_TAG_SIBLINGS )
        self._test_pairs_service_to_list( HC.CONTENT_TYPE_TAG_SIBLINGS )
        self._test_pairs_list_to_service( HC.CONTENT_TYPE_TAG_SIBLINGS )
        
    
    def test_migration_siblings_filter( self ):
        
        self._clear_db()
        
        self._set_up_services()
        
        self._add_count_filter_pairs_to_services( HC.CONTENT_TYPE_TAG_SIBLINGS )
        self._add_count_filter_mappings_to_services( HC.CONTENT_TYPE_TAG_SIBLINGS )
        self._test_pairs_htpa_to_list_count_filter( HC.CONTENT_TYPE_TAG_SIBLINGS )
        self._test_pairs_service_to_list_count_filter( HC.CONTENT_TYPE_TAG_SIBLINGS )
        
    
