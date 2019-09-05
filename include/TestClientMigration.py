from . import ClientCaches
from . import ClientConstants as CC
from . import ClientDB
from . import ClientImportFileSeeds
from . import ClientImportOptions
from . import ClientMigration
from . import ClientServices
from . import ClientTags
import collections
import hashlib
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusTagArchive
import os
import random
import shutil
import time
import unittest
from . import HydrusData
from . import HydrusGlobals as HG
from . import TestController

current_tag_pool = [ 'blonde hair', 'blue eyes', 'bodysuit', 'character:samus aran', 'series:metroid', 'studio:nintendo' ]
pending_tag_pool = [ 'favourites', 'kino', 'brown shirt', 'huge knees' ]
deleted_tag_pool = [ 'trash', 'ugly', 'character:smaus aran', 'red hair' ]

to_be_pended_tag_pool = [ 'clothing:high heels', 'firearm', 'puffy armpit' ]

class TestMigration( unittest.TestCase ):
    
    @classmethod
    def _clear_db( cls ):
        
        cls._delete_db()
        
        # class variable
        cls._db = ClientDB.DB( HG.test_controller, TestController.DB_DIR, 'client' )
        
    
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
        
        cls._db = ClientDB.DB( HG.test_controller, TestController.DB_DIR, 'client' )
        
    
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
        
        self.services_manager = ClientCaches.ServicesManager( self )
        
    
    def _do_fake_imports( self ):
        
        self._md5_to_sha256 = {}
        self._sha256_to_md5 = {}
        self._sha256_to_sha1 = {}
        
        self._my_files_sha256 = set()
        
        self._hashes_to_current_tags = {}
        self._hashes_to_pending_tags = {}
        self._hashes_to_deleted_tags = {}
        
        ( size, mime, width, height, duration, num_frames, has_audio, num_words ) = ( 65535, HC.IMAGE_JPEG, 640, 480, None, None, False, None )
        
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
                
                fake_file_import_job = ClientImportFileSeeds.FileImportJob( 'fake path' )
                
                fake_file_import_job._hash = hash
                fake_file_import_job._file_info = ( size, mime, width, height, duration, num_frames, has_audio, num_words )
                fake_file_import_job._extra_hashes = ( md5, sha1, sha512 )
                fake_file_import_job._phashes = [ os.urandom( 8 ) ]
                fake_file_import_job._file_import_options = ClientImportOptions.FileImportOptions()
                
                self.WriteSynchronous( 'import_file', fake_file_import_job )
                
                self._my_files_sha256.add( hash )
                
            
        
    
    def _add_tags_to_services( self ):
        
        content_updates = []
        
        for ( hash, tags ) in self._hashes_to_current_tags.items():
            
            for tag in tags:
                
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( hash, ) ) ) )
                
            
        
        for ( hash, tags ) in self._hashes_to_deleted_tags.items():
            
            for tag in tags:
                
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, ( hash, ) ) ) )
                
            
        
        service_keys_to_content_updates = { CC.LOCAL_TAG_SERVICE_KEY : content_updates }
        
        self.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
        
        content_updates = []
        
        for ( hash, tags ) in self._hashes_to_current_tags.items():
            
            for tag in tags:
                
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( hash, ) ) ) )
                
            
        
        for ( hash, tags ) in self._hashes_to_pending_tags.items():
            
            for tag in tags:
                
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, ( hash, ) ) ) )
                
            
        
        for ( hash, tags ) in self._hashes_to_deleted_tags.items():
            
            for tag in tags:
                
                content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( tag, ( hash, ) ) ) )
                
            
        
        service_keys_to_content_updates = { service_key : content_updates for service_key in self._test_tag_repo_service_keys.values() }
        
        self.WriteSynchronous( 'content_updates', service_keys_to_content_updates )
        
    
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
        
        tag_filter = ClientTags.TagFilter()
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'md5', None, tag_filter )
        
        expected_data = [ ( self._sha256_to_md5[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter )
        
        expected_data = list( self._hashes_to_current_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, CC.LOCAL_FILE_SERVICE_KEY, 'md5', None, tag_filter )
        
        expected_data = [ ( self._sha256_to_md5[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, CC.LOCAL_FILE_SERVICE_KEY, 'sha256', None, tag_filter )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        run_test( source, expected_data )
        
        # not all hashes, since hash type lookup only available for imported files
        hashes = random.sample( self._my_files_sha256, 25 )
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'md5', hashes, tag_filter )
        
        expected_data = [ ( self._sha256_to_md5[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', hashes, tag_filter )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        run_test( source, expected_data )
        
        # test desired hash type
        
        # not all hashes, since hash type lookup only available for imported files
        expected_data = [ ( self._sha256_to_sha1[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'sha1', None, tag_filter )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'sha1', None, tag_filter )
        
        run_test( source, expected_data )
        
        # do a test with specific hashes, so md5->sha1 does interim sha256 conversion
        # not all hashes, since hash type lookup only available for imported files
        hashes = random.sample( self._my_files_sha256, 25 )
        
        expected_data = [ ( self._sha256_to_sha1[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'sha1', hashes, tag_filter )
        
        run_test( source, expected_data )
        
        # tag filter
        
        tag_filter = ClientTags.TagFilter()
        
        tag_filter.SetRule( '', CC.FILTER_WHITELIST )
        tag_filter.SetRule( ':', CC.FILTER_BLACKLIST )
        
        source = ClientMigration.MigrationSourceHTA( self, md5_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'md5', None, tag_filter )
        
        expected_data = [ ( self._sha256_to_md5[ hash ], tag_filter.Filter( tags ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        expected_data = [ ( hash, tags ) for ( hash, tags ) in expected_data if len( tags ) > 0 ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceHTA( self, sha256_hta_path, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter )
        
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
        
        tag_filter = ClientTags.TagFilter()
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.LOCAL_TAG_SERVICE_KEY, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = list( self._hashes_to_current_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = list( self._hashes_to_current_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.LOCAL_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, CC.LOCAL_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        run_test( source, expected_data )
        
        # not all hashes, since hash type lookup only available for imported files
        hashes = random.sample( self._my_files_sha256, 25 )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.LOCAL_TAG_SERVICE_KEY, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', hashes, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', hashes, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in hashes ]
        
        run_test( source, expected_data )
        
        # test desired hash type
        
        # not all hashes, since hash type lookup only available for imported files
        expected_data = [ ( self._sha256_to_sha1[ hash ], tags ) for ( hash, tags ) in self._hashes_to_current_tags.items() if hash in self._my_files_sha256 ]
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.LOCAL_TAG_SERVICE_KEY, CC.COMBINED_FILE_SERVICE_KEY, 'sha1', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, CC.COMBINED_FILE_SERVICE_KEY, 'sha1', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        run_test( source, expected_data )
        
        # tag filter
        
        tag_filter = ClientTags.TagFilter()
        
        tag_filter.SetRule( '', CC.FILTER_WHITELIST )
        tag_filter.SetRule( ':', CC.FILTER_BLACKLIST )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.LOCAL_TAG_SERVICE_KEY, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tag_filter.Filter( tags ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        expected_data = [ ( hash, tags ) for ( hash, tags ) in expected_data if len( tags ) > 0 ]
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, ) )
        
        expected_data = [ ( hash, tag_filter.Filter( tags ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        expected_data = [ ( hash, tags ) for ( hash, tags ) in expected_data if len( tags ) > 0 ]
        
        run_test( source, expected_data )
        
        # test statuses
        
        tag_filter = ClientTags.TagFilter()
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, CC.LOCAL_TAG_SERVICE_KEY, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_DELETED, ) )
        
        expected_data = list( self._hashes_to_deleted_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_DELETED, ) )
        
        expected_data = list( self._hashes_to_deleted_tags.items() )
        
        run_test( source, expected_data )
        
        source = ClientMigration.MigrationSourceTagServiceMappings( self, tag_repo_service_key, CC.COMBINED_FILE_SERVICE_KEY, 'sha256', None, tag_filter, ( HC.CONTENT_STATUS_CURRENT, HC.CONTENT_STATUS_PENDING ) )
        
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
            
            self._db._weakref_media_result_cache = ClientCaches.MediaResultCache()
            
            hashes_to_media_results = { media_result.GetHash() : media_result for media_result in self.Read( 'media_results', list( self._hashes_to_current_tags.keys() ) ) }
            
            for ( hash, tags ) in expected_data:
                
                media_result = hashes_to_media_results[ hash ]
                
                t_m = media_result.GetTagsManager()
                
                if content_action == HC.CONTENT_UPDATE_ADD:
                    
                    current_tags = t_m.GetCurrent( tag_service_key )
                    
                    for tag in tags:
                        
                        self.assertIn( tag, current_tags )
                        
                    
                elif content_action == HC.CONTENT_UPDATE_DELETE:
                    
                    current_tags = t_m.GetCurrent( tag_service_key )
                    deleted_tags = t_m.GetDeleted( tag_service_key )
                    
                    for tag in tags:
                        
                        self.assertNotIn( tag, current_tags )
                        self.assertIn( tag, deleted_tags )
                        
                    
                elif content_action == HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD:
                    
                    deleted_tags = t_m.GetDeleted( tag_service_key )
                    
                    for tag in tags:
                        
                        self.assertNotIn( tag, deleted_tags )
                        
                    
                elif content_action == HC.CONTENT_UPDATE_PEND:
                    
                    pending_tags = t_m.GetPending( tag_service_key )
                    
                    for tag in tags:
                        
                        self.assertIn( tag, pending_tags )
                        
                    
                elif content_action == HC.CONTENT_UPDATE_PETITION:
                    
                    petitioned_tags = t_m.GetPetitioned( tag_service_key )
                    
                    for tag in tags:
                        
                        self.assertIn( tag, petitioned_tags )
                        
                    
                
            
        
        #
        
        # local add
        
        data = [ ( hash, set( random.sample( to_be_pended_tag_pool, 2 ) ) ) for hash in self._hashes_to_current_tags.keys() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_UPDATE_ADD, data )
        
        # local delete
        
        data = [ ( hash, set( random.sample( tags, 2 ) ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_UPDATE_DELETE, data )
        
        # local clear deletion record
        
        data = [ ( hash, set( random.sample( tags, 2 ) ) ) for ( hash, tags ) in self._hashes_to_deleted_tags.items() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, CC.LOCAL_TAG_SERVICE_KEY, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, data )
        
        # tag repo pend
        
        data = [ ( hash, set( random.sample( to_be_pended_tag_pool, 2 ) ) ) for hash in self._hashes_to_current_tags.keys() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, self._test_tag_repo_service_keys[1], HC.CONTENT_UPDATE_PEND, data )
        
        # tag repo petition
        
        data = [ ( hash, set( random.sample( tags, 2 ) ) ) for ( hash, tags ) in self._hashes_to_current_tags.items() ]
        
        source = ClientMigration.MigrationSourceList( self, data )
        
        run_test( source, self._test_tag_repo_service_keys[1], HC.CONTENT_UPDATE_PETITION, data )
        
    
    def test_migration( self ):
        
        # mappings
        
        self._set_up_services()
        self._do_fake_imports()
        self._add_tags_to_services()
        
        self._test_mappings_list_to_list()
        self._test_mappings_hta_to_list()
        self._test_mappings_list_to_hta()
        self._test_mappings_service_to_list()
        self._test_mappings_list_to_service()
        
        # parents
        
        # siblings
        
    
