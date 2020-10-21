import os
import time
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDB
from hydrus.client import ClientSearch
from hydrus.client import ClientServices
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.metadata import ClientTags

from hydrus.test import TestController

class TestClientDBTags( unittest.TestCase ):
    
    @classmethod
    def _create_db( cls ):
        
        # class variable
        cls._db = ClientDB.DB( HG.test_controller, TestController.DB_DIR, 'client' )
        
        HG.test_controller.SetRead( 'hash_status', ( CC.STATUS_UNKNOWN, None, '' ) )
        
    
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
        
        HG.test_controller.SetRead( 'hash_status', ( CC.STATUS_UNKNOWN, None, '' ) )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._delete_db()
        
    
    def _read( self, action, *args, **kwargs ): return TestClientDBTags._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestClientDBTags._db.Write( action, True, *args, **kwargs )
    
    def _clear_db( self ):
        
        TestClientDBTags._delete_db()
        
        TestClientDBTags._create_db()
        
        services = self._read( 'services' )
        
        TestClientDBTags.my_service_key = HydrusData.GenerateKey()
        TestClientDBTags.processing_service_key = HydrusData.GenerateKey()
        TestClientDBTags.public_service_key = HydrusData.GenerateKey()
        
        services.append( ClientServices.GenerateService( TestClientDBTags.my_service_key, HC.LOCAL_TAG, 'personal tags' ) ) # character
        services.append( ClientServices.GenerateService( TestClientDBTags.processing_service_key, HC.LOCAL_TAG, 'processing tags' ) ) # favourite
        services.append( ClientServices.GenerateService( TestClientDBTags.public_service_key, HC.TAG_REPOSITORY, 'public tags' ) ) # series, pending pp good
        
        self._write( 'update_services', services )
        
    
    def _sync_display( self ):
        
        for service_key in ( TestClientDBTags.my_service_key, TestClientDBTags.processing_service_key, TestClientDBTags.public_service_key ):
            
            still_work_to_do = True
            
            while still_work_to_do:
                
                still_work_to_do = self._write( 'sync_tag_display_maintenance', service_key, 1 )
                
            
        
    
    def test_siblings_pairs_lookup( self ):
        
        # add/delete pair
        # pend/petition pair
        
        # loop and whatever
        
        pass
        
    
    def test_siblings_application_lookup( self ):
        
        # three complicated lads that differ
        
        # test none
        # test one
        # test one from another service
        # test three
        # change order
        
        pass
        
    
    def test_siblings_application_autocomplete_counts( self ):
        
        # test none
        # test one
        # test one from another service
        # test three
        # change order
        
        pass
        
    
    def test_siblings_application_autocomplete_search( self ):
        
        # test none
        # test one
        # test one from another service
        # test three
        # change order
        
        pass
        
    
    def test_siblings_files_tag_autocomplete_counts_specific( self ):
        
        # set up some siblings
        # add file
        # remove file
        
        pass
        
    
    def test_siblings_files_tags_combined( self ):
        
        # set up some siblings
        # add file
        # remove file
        
        pass
        
    
    def test_siblings_files_tags_specific( self ):
        
        # set up some siblings
        # add file
        # remove file
        
        # do on a file in a specific domain and not in
        
        pass
        
    
    def test_siblings_tags_combined( self ):
        
        # set up some siblings
        
        # add/delete
        # pend/petition
        
        pass
        
    
    def test_siblings_tags_specific( self ):
        
        # set up some siblings
        
        # add/delete
        # pend/petition
        
        # do on a file in a specific domain and not in
        
        pass
        
    
    def test_tag_siblings( self ):
        
        # this sucks big time and should really be broken into specific scenarios to test add_file with tags and sibs etc...
        
        def test_ac( search_text, tag_service_key, file_service_key, expected_storage_tags_to_counts, expected_display_tags_to_counts ):
            
            tag_search_context = ClientSearch.TagSearchContext( tag_service_key )
            
            preds = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_STORAGE, tag_search_context, file_service_key, search_text = search_text )
            
            tags_to_counts = { pred.GetValue() : pred.GetAllCounts() for pred in preds }
            
            self.assertEqual( expected_storage_tags_to_counts, tags_to_counts )
            
            preds = self._read( 'autocomplete_predicates', ClientTags.TAG_DISPLAY_ACTUAL, tag_search_context, file_service_key, search_text = search_text )
            
            tags_to_counts = { pred.GetValue() : pred.GetAllCounts() for pred in preds }
            
            self.assertEqual( expected_display_tags_to_counts, tags_to_counts )
            
        
        samus_bad = bytes.fromhex( '5d884d84813beeebd59a35e474fa3e4742d0f2b6679faa7609b245ddbbd05444' )
        samus_both = bytes.fromhex( 'cdc67d3b377e6e1397ffa55edc5b50f6bdf4482c7a6102c6f27fa351429d6f49' )
        samus_good = bytes.fromhex( '9e7b8b5abc7cb11da32db05671ce926a2a2b701415d1b2cb77a28deea51010c3' )
        
        for on_local_files in ( False, True ):
            
            def test_no_sibs( force_no_local_files = False ):
                
                for do_regen_sibs in ( False, True ):
                    
                    if do_regen_sibs:
                        
                        self._write( 'regenerate_tag_siblings_cache' )
                        
                        self._sync_display()
                        
                    
                    for do_regen_display in ( False, True ):
                        
                        if do_regen_display:
                            
                            self._write( 'regenerate_tag_display_mappings_cache' )
                            
                            self._sync_display()
                            
                        
                        hash_ids_to_tags_managers = self._read( 'force_refresh_tags_managers', hash_ids )
                        
                        self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc bad', 'sameus aran' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc bad' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp bad' } )
                        
                        self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc bad', 'sameus aran', 'process these', 'pc bad', 'pp bad' } )
                        
                        self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc bad', 'mc good' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc bad', 'pc good', 'samus metroid' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp bad', 'pp good' } )
                        
                        self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc bad', 'mc good', 'process these', 'pc bad', 'pc good', 'samus metroid', 'pp bad', 'pp good' } )
                        
                        self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc good' } )
                        self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp good', 'character:samus aran' } )
                        
                        self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'process these', 'pc good', 'pp good', 'character:samus aran' } )
                        
                        test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ) }, { 'mc bad' : ( 2, None, 0, None ) } )
                        test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ) }, { 'pc bad' : ( 2, None, 0, None ) } )
                        test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ) }, { 'pp bad' : ( 0, None, 2, None ) } )
                        test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ) }, { 'sameus aran' : ( 1, None, 0, None ) } )
                        test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ) }, { 'samus metroid' : ( 1, None, 0, None ) } )
                        test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 0, None, 1, None ) } )
                        
                        if on_local_files and not force_no_local_files:
                            
                            test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ) }, { 'mc bad' : ( 2, None, 0, None ) } )
                            test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ) }, { 'pc bad' : ( 2, None, 0, None ) } )
                            test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ) }, { 'pp bad' : ( 0, None, 2, None ) } )
                            test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ) }, { 'sameus aran' : ( 1, None, 0, None ) } )
                            test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ) }, { 'samus metroid' : ( 1, None, 0, None ) } )
                            test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 0, None, 1, None ) } )
                            
                            test_ac( 'mc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ) }, { 'mc bad' : ( 2, None, 0, None ) } )
                            test_ac( 'pc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ) }, { 'pc bad' : ( 2, None, 0, None ) } )
                            test_ac( 'pp bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ) }, { 'pp bad' : ( 0, None, 2, None ) } )
                            test_ac( 'sameus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ) }, { 'sameus aran' : ( 1, None, 0, None ) } )
                            test_ac( 'samus metroid*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ) }, { 'samus metroid' : ( 1, None, 0, None ) } )
                            test_ac( 'samus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 0, None, 1, None ) } )
                            
                        else:
                            
                            test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            
                            test_ac( 'mc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'pc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'pp bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'sameus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'samus metroid*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            test_ac( 'samus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                            
                        
                    
                
            
            self._clear_db()
            
            hashes = { samus_bad, samus_both, samus_good }
            
            media_results = self._read( 'media_results', hashes )
            
            for media_result in media_results:
                
                if media_result.GetHash() == samus_bad:
                    
                    samus_bad_hash_id = media_result.GetHashId()
                    
                elif media_result.GetHash() == samus_both:
                    
                    samus_both_hash_id = media_result.GetHashId()
                    
                elif media_result.GetHash() == samus_good:
                    
                    samus_good_hash_id = media_result.GetHashId()
                    
                
            
            hash_ids = ( samus_bad_hash_id, samus_both_hash_id, samus_good_hash_id )
            
            service_keys_to_content_updates = {}
            
            content_updates = []
            
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( samus_bad, ) ) ) for tag in ( 'mc bad', 'sameus aran' ) ) )
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( samus_both, ) ) ) for tag in ( 'mc bad', 'mc good', ) ) )
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( samus_good, ) ) ) for tag in ( 'mc good', ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.my_service_key ] = content_updates
            
            content_updates = []
            
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( samus_bad, samus_both, samus_good ) ) ) for tag in ( 'process these', ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.processing_service_key ] = content_updates
            
            content_updates = []
            
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( samus_bad, ) ) ) for tag in ( 'pc bad', ) ) )
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( samus_both, ) ) ) for tag in ( 'pc bad', 'pc good', 'samus metroid' ) ) )
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( tag, ( samus_good, ) ) ) for tag in ( 'pc good', ) ) )
            
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, ( samus_bad, ) ) ) for tag in ( 'pp bad', ) ) )
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, ( samus_both, ) ) ) for tag in ( 'pp bad', 'pp good' ) ) )
            content_updates.extend( ( HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( tag, ( samus_good, ) ) ) for tag in ( 'pp good', 'character:samus aran' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.public_service_key ] = content_updates
            
            self._write( 'content_updates', service_keys_to_content_updates )
            
            self._sync_display()
            
            # start out, no sibs
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
            test_no_sibs( force_no_local_files = True )
            
            if on_local_files:
                
                # doing this again tests a very simple add_file
                
                for filename in ( 'muh_jpg.jpg', 'muh_png.png', 'muh_apng.png' ):
                    
                    path = os.path.join( HC.STATIC_DIR, 'testing', filename )
                    
                    file_import_job = ClientImportFileSeeds.FileImportJob( path )
                    
                    file_import_job.GenerateHashAndStatus()
                    
                    file_import_job.GenerateInfo()
                    
                    self._write( 'import_file', file_import_job )
                    
                
                test_no_sibs()
                
            
            # some sibs that should do nothing
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'process these', 'nope' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.my_service_key ] = content_updates
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'mc bad', 'mc wrong' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'pc bad', 'pc wrong' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'pp bad', 'pp wrong' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'sameus aran', 'link' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'link', 'zelda' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.processing_service_key ] = content_updates
            
            self._write( 'content_updates', service_keys_to_content_updates )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), { 'process these' : 'nope' } )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), { 'mc bad' : 'mc wrong', 'pc bad' : 'pc wrong', 'pp bad' : 'pp wrong', 'sameus aran' : 'zelda', 'link' : 'zelda' } )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
            test_no_sibs()
            
            # remove them
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, ( 'process these', 'nope' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.my_service_key ] = content_updates
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, ( 'mc bad', 'mc wrong' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, ( 'pc bad', 'pc wrong' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, ( 'pp bad', 'pp wrong' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, ( 'sameus aran', 'link' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, ( 'link', 'zelda' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.processing_service_key ] = content_updates
            
            self._write( 'content_updates', service_keys_to_content_updates )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
            test_no_sibs()
            
            # now some simple sibs
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'mc bad', 'mc good' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'sameus aran', 'samus metroid' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.my_service_key ] = content_updates
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'pc bad', 'pc good' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'pp bad', 'pp good' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'samus metroid', 'character:samus aran' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.public_service_key ] = content_updates
            
            self._write( 'content_updates', service_keys_to_content_updates )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), { 'mc bad' : 'mc good', 'sameus aran' : 'samus metroid' } )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), { 'pc bad' : 'pc good', 'pp bad' : 'pp good', 'samus metroid' : 'character:samus aran' } )
            
            for do_regen_sibs in ( False, True ):
                
                if do_regen_sibs:
                    
                    self._write( 'regenerate_tag_siblings_cache' )
                    
                    self._sync_display()
                    
                
                for do_regen_display in ( False, True ):
                    
                    if do_regen_display:
                        
                        self._write( 'regenerate_tag_display_mappings_cache' )
                        
                        self._sync_display()
                        
                    
                    hash_ids_to_tags_managers = self._read( 'force_refresh_tags_managers', hash_ids )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'samus metroid' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc good' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp good' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'samus metroid', 'process these', 'pc good', 'pp good' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'mc good' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc good', 'pc good', 'character:samus aran' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp good', 'pp good' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'mc good', 'process these', 'pc good', 'pc good', 'character:samus aran', 'pp good', 'pp good' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc good' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp good', 'character:samus aran' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'process these', 'pc good', 'pp good', 'character:samus aran' } )
                    
                    # now we get more write a/c suggestions, and accurated merged read a/c values
                    test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ), 'mc good' : ( 2, None, 0, None ) }, { 'mc good' : ( 3, None, 0, None ) } )
                    test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ), 'pc good' : ( 2, None, 0, None ) }, { 'pc good' : ( 3, None, 0, None ) } )
                    test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ), 'pp good' : ( 0, None, 2, None ) }, { 'pp good' : ( 0, None, 3, None ) } )
                    test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ) }, { 'samus metroid' : ( 1, None, 0, None ) } )
                    test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, None, 1, None ) } )
                    test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, None, 1, None ) } )
                    
                    if on_local_files:
                        
                        # same deal, just smaller file domain
                        test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ), 'mc good' : ( 2, None, 0, None ) }, { 'mc good' : ( 3, None, 0, None ) } )
                        test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ), 'pc good' : ( 2, None, 0, None ) }, { 'pc good' : ( 3, None, 0, None ) } )
                        test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ), 'pp good' : ( 0, None, 2, None ) }, { 'pp good' : ( 0, None, 3, None ) } )
                        test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ) }, { 'samus metroid' : ( 1, None, 0, None ) } )
                        test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, None, 1, None ) } )
                        test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, None, 1, None ) } )
                        
                        test_ac( 'mc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ), 'mc good' : ( 2, None, 0, None ) }, { 'mc good' : ( 3, None, 0, None ) } )
                        test_ac( 'pc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ), 'pc good' : ( 2, None, 0, None ) }, { 'pc good' : ( 3, None, 0, None ) } )
                        test_ac( 'pp bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ), 'pp good' : ( 0, None, 2, None ) }, { 'pp good' : ( 0, None, 3, None ) } )
                        # here the write a/c gets funky because of all known tags. finding counts for disjoint yet now merged sibling suggestions even though not on same tag domain
                        # slightly odd situation, but we'll want to clear it up
                        # this is cleared up UI side when it does sibling_tag_id filtering based on the tag service we are pending to, but it shows that a/c fetch needs an optional sibling_tag_service_key
                        # this is a job for tag search context
                        # read a/c counts are fine
                        test_ac( 'sameus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ), 'samus metroid' : ( 1, None, 0, None ) }, { 'samus metroid' : ( 1, None, 0, None ) } )
                        test_ac( 'samus metroid*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ), 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 1, None, 1, None ) } )
                        test_ac( 'samus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 1, None, 1, None ) } )
                        
                    else:
                        
                        test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        
                        test_ac( 'mc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'pc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'pp bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'sameus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'samus metroid*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'samus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        
                    
                
            
            # remove the application
            
            master_service_keys_to_parent_applicable_service_keys = { TestClientDBTags.my_service_key : [], TestClientDBTags.processing_service_key : [], TestClientDBTags.public_service_key : [] }
            
            master_service_keys_to_sibling_applicable_service_keys = { TestClientDBTags.my_service_key : [], TestClientDBTags.processing_service_key : [], TestClientDBTags.public_service_key : [] }
            
            self._write( 'tag_display_application', master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
            test_no_sibs()
            
            # apply across to both, which should do A->B->C chain
            
            master_service_keys_to_sibling_applicable_service_keys = { TestClientDBTags.my_service_key : [ TestClientDBTags.my_service_key, TestClientDBTags.public_service_key ], TestClientDBTags.processing_service_key : [], TestClientDBTags.public_service_key : [ TestClientDBTags.my_service_key, TestClientDBTags.public_service_key ] }
            
            self._write( 'tag_display_application', master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), { 'mc bad' : 'mc good', 'sameus aran' : 'character:samus aran', 'pc bad' : 'pc good', 'pp bad' : 'pp good', 'samus metroid' : 'character:samus aran' } )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), { 'mc bad' : 'mc good', 'sameus aran' : 'character:samus aran', 'pc bad' : 'pc good', 'pp bad' : 'pp good', 'samus metroid' : 'character:samus aran' } )
            
            for do_regen_sibs in ( False, True ):
                
                if do_regen_sibs:
                    
                    self._write( 'regenerate_tag_siblings_cache' )
                    
                    self._sync_display()
                    
                
                for do_regen_display in ( False, True ):
                    
                    if do_regen_display:
                        
                        self._write( 'regenerate_tag_display_mappings_cache' )
                        
                        self._sync_display()
                        
                    
                    hash_ids_to_tags_managers = self._read( 'force_refresh_tags_managers', hash_ids )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'character:samus aran' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc good' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp good' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_bad_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'character:samus aran', 'process these', 'pc good', 'pp good' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'mc good' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc good', 'pc good', 'character:samus aran' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp good', 'pp good' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_both_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'mc good', 'process these', 'pc good', 'pc good', 'character:samus aran', 'pp good', 'pp good' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.my_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.processing_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'process these' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrent( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pc good' } )
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetPending( TestClientDBTags.public_service_key, ClientTags.TAG_DISPLAY_ACTUAL ), { 'pp good', 'character:samus aran' } )
                    
                    self.assertEqual( hash_ids_to_tags_managers[ samus_good_hash_id ].GetCurrentAndPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_ACTUAL ), { 'mc good', 'process these', 'pc good', 'pp good', 'character:samus aran' } )
                    
                    # now we get more write a/c suggestions, and accurated merged read a/c values
                    test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ), 'mc good' : ( 2, None, 0, None ) }, { 'mc good' : ( 3, None, 0, None ) } )
                    test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ), 'pc good' : ( 2, None, 0, None ) }, { 'pc good' : ( 3, None, 0, None ) } )
                    test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ), 'pp good' : ( 0, None, 2, None ) }, { 'pp good' : ( 0, None, 3, None ) } )
                    test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ) }, { 'character:samus aran' : ( 1, None, 0, None ) } )
                    test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, None, 1, None ) } )
                    test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.COMBINED_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, None, 1, None ) } )
                    
                    if on_local_files:
                        
                        # same deal, just smaller file domain
                        test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ), 'mc good' : ( 2, None, 0, None ) }, { 'mc good' : ( 3, None, 0, None ) } )
                        test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ), 'pc good' : ( 2, None, 0, None ) }, { 'pc good' : ( 3, None, 0, None ) } )
                        test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ), 'pp good' : ( 0, None, 2, None ) }, { 'pp good' : ( 0, None, 3, None ) } )
                        test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ) }, { 'character:samus aran' : ( 1, None, 0, None ) } )
                        test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, None, 1, None ) } )
                        test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, { 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, None, 1, None ) } )
                        
                        test_ac( 'mc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'mc bad' : ( 2, None, 0, None ), 'mc good' : ( 2, None, 0, None ) }, { 'mc good' : ( 3, None, 0, None ) } )
                        test_ac( 'pc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'pc bad' : ( 2, None, 0, None ), 'pc good' : ( 2, None, 0, None ) }, { 'pc good' : ( 3, None, 0, None ) } )
                        test_ac( 'pp bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'pp bad' : ( 0, None, 2, None ), 'pp good' : ( 0, None, 2, None ) }, { 'pp good' : ( 0, None, 3, None ) } )
                        # here the write a/c gets funky because of all known tags. finding counts for disjoint yet now merged sibling suggestions even though not on same tag domain
                        # slightly odd situation, but we'll want to clear it up
                        # this is cleared up UI side when it does sibling_tag_id filtering based on the tag service we are pending to, but it shows that a/c fetch needs an optional sibling_tag_service_key
                        # this is a job for tag search context
                        # read a/c counts are fine
                        test_ac( 'sameus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ), 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, 2, 1, None ) } )
                        test_ac( 'samus metroid*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ), 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, 2, 1, None ) } )
                        test_ac( 'samus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, { 'sameus aran' : ( 1, None, 0, None ), 'samus metroid' : ( 1, None, 0, None ), 'character:samus aran' : ( 0, None, 1, None ) }, { 'character:samus aran' : ( 1, 2, 1, None ) } )
                        
                    else:
                        
                        test_ac( 'mc bad*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'pc bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'pp bad*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'sameus aran*', TestClientDBTags.my_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'samus metroid*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'samus aran*', TestClientDBTags.public_service_key, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        
                        test_ac( 'mc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'pc bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'pp bad*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'sameus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'samus metroid*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        test_ac( 'samus aran*', CC.COMBINED_TAG_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY, {}, {} )
                        
                    
                
            
            # delete and petition, should remove it all
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, ( 'mc bad', 'mc good' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_DELETE, ( 'sameus aran', 'samus metroid' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.my_service_key ] = content_updates
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, ( 'pc bad', 'pc good' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, ( 'pp bad', 'pp good' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, ( 'samus metroid', 'character:samus aran' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.public_service_key ] = content_updates
            
            self._write( 'content_updates', service_keys_to_content_updates )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
            test_no_sibs()
            
            # now test de-looping
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'good answer', 'process these' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.my_service_key ] = content_updates
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'process these', 'lmao' ) ) )
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'lmao', 'good answer' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.processing_service_key ] = content_updates
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_PETITION, ( 'lmao', 'process these' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.public_service_key ] = content_updates
            
            self._write( 'content_updates', service_keys_to_content_updates )
            
            self._sync_display()
            
            master_service_keys_to_sibling_applicable_service_keys = { TestClientDBTags.my_service_key : [], TestClientDBTags.processing_service_key : [ TestClientDBTags.processing_service_key, TestClientDBTags.my_service_key ], TestClientDBTags.public_service_key : [] }
            
            self._write( 'tag_display_application', master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), { 'process these' : 'good answer', 'lmao' : 'good answer' } )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
            master_service_keys_to_sibling_applicable_service_keys = { TestClientDBTags.my_service_key : [], TestClientDBTags.processing_service_key : [ TestClientDBTags.processing_service_key, TestClientDBTags.public_service_key ], TestClientDBTags.public_service_key : [] }
            
            self._write( 'tag_display_application', master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), { 'process these' : 'good answer', 'lmao' : 'good answer' } )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
            master_service_keys_to_sibling_applicable_service_keys = { TestClientDBTags.my_service_key : [], TestClientDBTags.processing_service_key : [ TestClientDBTags.processing_service_key, TestClientDBTags.my_service_key, TestClientDBTags.public_service_key ], TestClientDBTags.public_service_key : [] }
            
            self._write( 'tag_display_application', master_service_keys_to_sibling_applicable_service_keys, master_service_keys_to_parent_applicable_service_keys )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), {} )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ), { 'process these' : 'good answer', 'lmao' : 'good answer' } )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
            content_updates = []
            
            content_updates.append( HydrusData.ContentUpdate( HC.CONTENT_TYPE_TAG_SIBLINGS, HC.CONTENT_UPDATE_ADD, ( 'good answer', 'process these' ) ) )
            
            service_keys_to_content_updates[ TestClientDBTags.processing_service_key ] = content_updates
            
            service_keys_to_content_updates[ TestClientDBTags.public_service_key ] = content_updates
            
            self._write( 'content_updates', service_keys_to_content_updates )
            
            self._sync_display()
            
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.my_service_key ), {} )
            self.assertEqual( len( self._read( 'tag_siblings_all_ideals', TestClientDBTags.processing_service_key ) ), 2 )
            self.assertEqual( self._read( 'tag_siblings_all_ideals', TestClientDBTags.public_service_key ), {} )
            
        


    '''
class TestTagParents( unittest.TestCase ):
    
    @classmethod
    def setUpClass( cls ):
        
        cls._first_key = HydrusData.GenerateKey()
        cls._second_key = HydrusData.GenerateKey()
        cls._third_key = HydrusData.GenerateKey()
        
        first_dict = HydrusData.default_dict_set()
        
        first_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'current_a', 'current_b' ), ( 'child', 'mother' ), ( 'child', 'father' ), ( 'sister', 'mother' ), ( 'sister', 'father' ), ( 'brother', 'mother' ), ( 'brother', 'father' ), ( 'mother', 'grandmother' ), ( 'mother', 'grandfather' ), ( 'aunt', 'grandmother' ), ( 'aunt', 'grandfather' ), ( 'cousin', 'aunt' ), ( 'cousin', 'uncle' ), ( 'closed_loop', 'closed_loop' ), ( 'loop_a', 'loop_b' ), ( 'loop_b', 'loop_c' ) }
        first_dict[ HC.CONTENT_STATUS_DELETED ] = { ( 'deleted_a', 'deleted_b' ) }
        
        second_dict = HydrusData.default_dict_set()
        
        second_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'loop_c', 'loop_a' ) }
        second_dict[ HC.CONTENT_STATUS_DELETED ] = { ( 'current_a', 'current_b' ) }
        second_dict[ HC.CONTENT_STATUS_PENDING ] = { ( 'pending_a', 'pending_b' ) }
        second_dict[ HC.CONTENT_STATUS_PETITIONED ] = { ( 'petitioned_a', 'petitioned_b' ) }
        
        third_dict = HydrusData.default_dict_set()
        
        third_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'petitioned_a', 'petitioned_b' ) }
        third_dict[ HC.CONTENT_STATUS_DELETED ] = { ( 'pending_a', 'pending_b' ) }
        
        tag_parents = collections.defaultdict( HydrusData.default_dict_set )
        
        tag_parents[ cls._first_key ] = first_dict
        tag_parents[ cls._second_key ] = second_dict
        tag_parents[ cls._third_key ] = third_dict
        
        HG.test_controller.SetRead( 'tag_parents', tag_parents )
        
        cls._tag_parents_manager = ClientManagers.TagParentsManager( HG.client_controller )
        
    
    def test_expand_predicates( self ):
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'grandmother', min_current_count = 10 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'grandfather', min_current_count = 15 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'not_exist', min_current_count = 20 ) )
        
        self.assertEqual( self._tag_parents_manager.ExpandPredicates( CC.COMBINED_TAG_SERVICE_KEY, predicates ), predicates )
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'child', min_current_count = 10 ) )
        
        results = []
        
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'child', min_current_count = 10 ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'mother' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'father' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'grandmother' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'grandfather' ) )
        
        self.assertEqual( set( self._tag_parents_manager.ExpandPredicates( CC.COMBINED_TAG_SERVICE_KEY, predicates ) ), set( results ) )
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'series' ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'child', min_current_count = 10 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'cousin', min_current_count = 5 ) )
        
        results = []
        
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'series' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'child', min_current_count = 10 ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'mother' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'father' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'grandmother' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'grandfather' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'cousin', min_current_count = 5 ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'aunt' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'uncle' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'grandmother' ) )
        results.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'grandfather' ) )
        
        self.assertEqual( set( self._tag_parents_manager.ExpandPredicates( CC.COMBINED_TAG_SERVICE_KEY, predicates ) ), set( results ) )
        
    
    def test_expand_tags( self ):
        
        tags = { 'grandmother', 'grandfather' }
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, tags ), tags )
        
        tags = { 'child', 'cousin' }
        
        results = { 'child', 'mother', 'father', 'grandmother', 'grandfather', 'cousin', 'aunt', 'uncle', 'grandmother', 'grandfather' }
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, tags ), results )
        
    
    def test_grandparents( self ):
        
        self.assertEqual( set( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'child' ) ), { 'mother', 'father', 'grandmother', 'grandfather' } )
        self.assertEqual( set( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'mother' ) ), { 'grandmother', 'grandfather' } )
        self.assertEqual( set( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'grandmother' ) ), set() )
        
    
    def test_current_overwrite( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'current_a' ), [ 'current_b' ] )
        self.assertEqual( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'current_b' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, [ 'current_a' ] ), { 'current_a', 'current_b' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, [ 'current_b' ] ), { 'current_b' } )
        
    
    def test_deleted( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'deleted_a' ), [] )
        self.assertEqual( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'deleted_b' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, [ 'deleted_a' ] ), { 'deleted_a' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, [ 'deleted_b' ] ), { 'deleted_b' } )
        
    
    def test_no_loop( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'closed_loop' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, [ 'closed_loop' ] ), { 'closed_loop' } )
        
    
    def test_not_exist( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'not_exist' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, [ 'not_exist' ] ), { 'not_exist' } )
        
    
    def test_pending_overwrite( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'pending_a' ), [ 'pending_b' ] )
        self.assertEqual( self._tag_parents_manager.GetParents( CC.COMBINED_TAG_SERVICE_KEY, 'pending_b' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, [ 'pending_a' ] ), { 'pending_a', 'pending_b' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( CC.COMBINED_TAG_SERVICE_KEY, [ 'pending_b' ] ), { 'pending_b' } )
        
    '''
