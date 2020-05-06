import collections
from hydrus.client import ClientCaches
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientManagers
from hydrus.client import ClientMedia
from hydrus.client import ClientMediaManagers
from hydrus.client import ClientSearch
from hydrus.client import ClientTags
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
import os
import unittest

class TestMergeTagsManagers( unittest.TestCase ):
    
    def test_merge( self ):
        
        first = HydrusData.GenerateKey()
        second = HydrusData.GenerateKey()
        third = HydrusData.GenerateKey()
        
        #
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ first ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_1', 'series:blame!' }
        
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate_1', 'character:cibo' }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_DELETED ] = { 'current_1' }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'pending_1', 'creator:tsutomu nihei' }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_PETITIONED ] = { 'petitioned_1' }
        
        service_keys_to_statuses_to_tags[ third ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate', 'current_duplicate_1' }
        service_keys_to_statuses_to_tags[ third ][ HC.CONTENT_STATUS_PENDING ] = { 'volume:3' }
        
        tags_manager_1 = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags )
        
        #
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ first ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_2', 'series:blame!', 'chapter:1' }
        service_keys_to_statuses_to_tags[ first ][ HC.CONTENT_STATUS_DELETED ] = { 'deleted_2' }
        
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate'  }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'architecture', 'chapter:2' }
        
        service_keys_to_statuses_to_tags[ third ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate' }
        
        tags_manager_2 = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags )
        
        #
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'page:4', 'page:5' }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'title:double page spread' }
        
        tags_manager_3 = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags )
        
        #
        
        tags_managers = ( tags_manager_1, tags_manager_2, tags_manager_3 )
        
        tags_manager = ClientMediaManagers.TagsManager.MergeTagsManagers( tags_managers )
        
        #
        
        self.assertEqual( tags_manager.GetNamespaceSlice( ( 'character', ), ClientTags.TAG_DISPLAY_SIBLINGS_AND_PARENTS ), frozenset( { 'character:cibo' } ) )
        
    
class TestTagsManager( unittest.TestCase ):
    
    @classmethod
    def setUpClass( cls ):
        
        cls._first_key = HydrusData.GenerateKey()
        cls._second_key = HydrusData.GenerateKey()
        cls._third_key = HydrusData.GenerateKey()
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ cls._first_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'current', '\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1' }
        service_keys_to_statuses_to_tags[ cls._first_key ][ HC.CONTENT_STATUS_DELETED ] = { 'deleted' }
        
        service_keys_to_statuses_to_tags[ cls._second_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'deleted', '\u2835' }
        service_keys_to_statuses_to_tags[ cls._second_key ][ HC.CONTENT_STATUS_DELETED ] = { 'current' }
        service_keys_to_statuses_to_tags[ cls._second_key ][ HC.CONTENT_STATUS_PENDING ] = { 'pending' }
        service_keys_to_statuses_to_tags[ cls._second_key ][ HC.CONTENT_STATUS_PETITIONED ] = { 'petitioned' }
        
        service_keys_to_statuses_to_tags[ cls._third_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'petitioned' }
        service_keys_to_statuses_to_tags[ cls._third_key ][ HC.CONTENT_STATUS_DELETED ] = { 'pending' }
        
        cls._tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags )
        
        cls._service_keys_to_statuses_to_tags = service_keys_to_statuses_to_tags
        
        #
        
        cls._pending_service_key = HydrusData.GenerateKey()
        cls._content_update_service_key = HydrusData.GenerateKey()
        cls._reset_service_key = HydrusData.GenerateKey()
        
        other_service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        other_service_keys_to_statuses_to_tags[ cls._pending_service_key ][ HC.CONTENT_STATUS_PENDING ] = { 'pending' }
        other_service_keys_to_statuses_to_tags[ cls._pending_service_key ][ HC.CONTENT_STATUS_PETITIONED ] = { 'petitioned' }
        
        other_service_keys_to_statuses_to_tags[ cls._reset_service_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'reset_current' }
        other_service_keys_to_statuses_to_tags[ cls._reset_service_key ][ HC.CONTENT_STATUS_DELETED ] = { 'reset_deleted' }
        other_service_keys_to_statuses_to_tags[ cls._reset_service_key ][ HC.CONTENT_STATUS_PENDING ] = { 'reset_pending' }
        other_service_keys_to_statuses_to_tags[ cls._reset_service_key ][ HC.CONTENT_STATUS_PETITIONED ] = { 'reset_petitioned' }
        
        cls._other_tags_manager = ClientMediaManagers.TagsManager( other_service_keys_to_statuses_to_tags )
        
        cls._other_service_keys_to_statuses_to_tags = other_service_keys_to_statuses_to_tags
        
    
    def test_delete_pending( self ):
        
        self.assertEqual( self._other_tags_manager.GetPending( self._pending_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'pending' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._pending_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'petitioned' } )
        
        self._other_tags_manager.DeletePending( self._pending_service_key )
        
        self.assertEqual( self._other_tags_manager.GetPending( self._pending_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._pending_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
    
    def test_get_current( self ):
        
        self.assertEqual( self._tags_manager.GetCurrent( self._first_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'current', '\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1' } )
        self.assertEqual( self._tags_manager.GetCurrent( self._second_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'deleted', '\u2835' } )
        self.assertEqual( self._tags_manager.GetCurrent( self._third_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'petitioned' } )
        
        self.assertEqual( self._tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ), { 'current', 'deleted', '\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1', 'petitioned' } )
        
    
    def test_get_deleted( self ):
        
        self.assertEqual( self._tags_manager.GetDeleted( self._first_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'deleted' } )
        self.assertEqual( self._tags_manager.GetDeleted( self._second_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'current' } )
        self.assertEqual( self._tags_manager.GetDeleted( self._third_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'pending' } )
        
        self.assertEqual( self._tags_manager.GetDeleted( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ), { 'deleted', 'current', 'pending' } )
        
    
    def test_get_namespace_slice( self ):
        
        self.assertEqual( self._tags_manager.GetNamespaceSlice( ( 'creator', 'series' ), ClientTags.TAG_DISPLAY_SIBLINGS_AND_PARENTS ), frozenset( { 'creator:tsutomu nihei', 'series:blame!' } ) )
        self.assertEqual( self._tags_manager.GetNamespaceSlice( [], ClientTags.TAG_DISPLAY_SIBLINGS_AND_PARENTS ), frozenset() )
        
    
    def test_get_num_tags( self ):
        
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._first_key, include_current_tags = False, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._first_key, include_current_tags = True, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 8 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._first_key, include_current_tags = False, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._first_key, include_current_tags = True, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 8 )
        
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._second_key, include_current_tags = False, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._second_key, include_current_tags = True, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 2 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._second_key, include_current_tags = False, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._second_key, include_current_tags = True, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 3 )
        
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._third_key, include_current_tags = False, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._third_key, include_current_tags = True, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._third_key, include_current_tags = False, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = self._third_key, include_current_tags = True, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 1 )
        
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = False, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 10 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = False, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearch.TagSearchContext( service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 11 )
        
    
    def test_get_pending( self ):
        
        self.assertEqual( self._tags_manager.GetPending( self._first_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._tags_manager.GetPending( self._second_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'pending' } )
        self.assertEqual( self._tags_manager.GetPending( self._third_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertEqual( self._tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ), { 'pending' } )
        
    
    def test_get_petitioned( self ):
        
        self.assertEqual( self._tags_manager.GetPetitioned( self._first_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._tags_manager.GetPetitioned( self._second_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'petitioned' } )
        self.assertEqual( self._tags_manager.GetPetitioned( self._third_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertEqual( self._tags_manager.GetPetitioned( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ), { 'petitioned' } )
        
    
    def test_get_service_keys_to_statuses_to_tags( self ):
        
        s = self._tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
        
        self.assertEqual( s[ self._first_key ], self._service_keys_to_statuses_to_tags[ self._first_key ] )
        self.assertEqual( s[ self._second_key ], self._service_keys_to_statuses_to_tags[ self._second_key ] )
        self.assertEqual( s[ self._third_key ], self._service_keys_to_statuses_to_tags[ self._third_key ] )
        
    
    def test_get_statuses_to_tags( self ):
        
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._first_key, ClientTags.TAG_DISPLAY_STORAGE ), self._service_keys_to_statuses_to_tags[ self._first_key ] )
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._second_key, ClientTags.TAG_DISPLAY_STORAGE ), self._service_keys_to_statuses_to_tags[ self._second_key ] )
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._third_key, ClientTags.TAG_DISPLAY_STORAGE ), self._service_keys_to_statuses_to_tags[ self._third_key ] )
        
    
    def test_has_tag( self ):
        
        self.assertTrue( self._tags_manager.HasTag( '\u2835', ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertFalse( self._tags_manager.HasTag( 'not_exist', ClientTags.TAG_DISPLAY_STORAGE ) )
        
    
    def test_process_content_update( self ):
        
        hashes = { HydrusData.GenerateKey() for i in range( 6 ) }
        
        #
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE, ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'hello', hashes ), reason = 'reason' )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'hello', hashes ), reason = 'reason' )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
    
    def test_reset_service( self ):
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._reset_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'reset_current' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._reset_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'reset_deleted' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._reset_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'reset_pending' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._reset_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'reset_petitioned' } )
        
        self._other_tags_manager.ResetService( self._reset_service_key )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._reset_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._reset_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._reset_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._reset_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
    
class TestTagDisplayManager( unittest.TestCase ):
    
    def test_tag_filtering( self ):
        
        filter_pages = ClientTags.TagFilter()
        
        filter_pages.SetRule( 'page:', CC.FILTER_BLACKLIST )
        
        tag_display_manager = ClientTags.TagDisplayManager()
        
        tag_display_manager.SetTagFilter( ClientTags.TAG_DISPLAY_SELECTION_LIST, CC.COMBINED_TAG_SERVICE_KEY, filter_pages )
        
        tags = { 'character:samus aran', 'series:metroid', 'page:17' }
        
        #
        
        self.assertFalse( tag_display_manager.FiltersTags( ClientTags.TAG_DISPLAY_STORAGE, CC.COMBINED_TAG_SERVICE_KEY ) )
        
        storage_tags = tag_display_manager.FilterTags( ClientTags.TAG_DISPLAY_STORAGE, CC.COMBINED_TAG_SERVICE_KEY, tags )
        
        self.assertEqual( storage_tags, tags )
        
        #
        
        self.assertTrue( tag_display_manager.FiltersTags( ClientTags.TAG_DISPLAY_SELECTION_LIST, CC.COMBINED_TAG_SERVICE_KEY ) )
        
        selection_tags = tag_display_manager.FilterTags( ClientTags.TAG_DISPLAY_SELECTION_LIST, CC.COMBINED_TAG_SERVICE_KEY, tags )
        
        self.assertTrue( len( selection_tags ) < len( tags ) )
        
        self.assertEqual( selection_tags, filter_pages.Filter( tags ) )
        
    
class TestTagObjects( unittest.TestCase ):
    
    def test_parsed_autocomplete_text( self ):
        
        def bool_tests( pat: ClientSearch.ParsedAutocompleteText, values ):
            
            self.assertEqual( pat.IsAcceptableForFiles(), values[0] )
            self.assertEqual( pat.IsAcceptableForTags(), values[1] )
            self.assertEqual( pat.IsEmpty(), values[2] )
            self.assertEqual( pat.IsExplicitWildcard(), values[3] )
            self.assertEqual( pat.IsNamespaceSearch(), values[4] )
            self.assertEqual( pat.IsTagSearch(), values[5] )
            self.assertEqual( pat.inclusive, values[6] )
            
        
        def search_text_tests( pat: ClientSearch.ParsedAutocompleteText, values ):
            
            self.assertEqual( pat.GetSearchText( False ), values[0] )
            self.assertEqual( pat.GetSearchText( True ), values[1] )
            
        
        def read_predicate_tests( pat: ClientSearch.ParsedAutocompleteText, values ):
            
            self.assertEqual( pat.GetImmediateFileSearchPredicate(), values[0] )
            self.assertEqual( pat.GetNonTagFileSearchPredicates(), values[1] )
            
        
        def write_predicate_tests( pat: ClientSearch.ParsedAutocompleteText, values ):
            
            self.assertEqual( pat.GetAddTagPredicate(), values[0] )
            
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '', True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ '', '' ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-', True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        search_text_tests( parsed_autocomplete_text, [ '', '' ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'samus', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-samus', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, False ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus', inclusive = False ), [] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'samus*', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus*', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'samus*' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'samus*' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'character:samus ', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'character:samus', 'character:samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-character:samus ', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, False ] )
        search_text_tests( parsed_autocomplete_text, [ 'character:samus', 'character:samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus', inclusive = False ), [] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 's*s', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s', 's*s*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s*' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s*' ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-s*s', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, False ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s', 's*s*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s*', inclusive = False ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s*', inclusive = False ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s', inclusive = False ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'metroid:', True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'metroid' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'metroid' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-metroid:', True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, False ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'metroid', inclusive = False ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'metroid', inclusive = False ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 's*s a*n', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s a*n', 's*s a*n*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s a*n*' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s a*n*' ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s a*n' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( ' samus ', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '[samus]', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, '[samus]' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, '[samus]' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'creator-id:', True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'creator-id' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'creator-id' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'creator-id:*', True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, True, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'creator-id' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'creator-id' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'n*n g*s e*n:as*ka', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'n*n g*s e*n:as*ka', 'n*n g*s e*n:as*ka*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'n*n g*s e*n:as*ka*' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'n*n g*s e*n:as*ka*' ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'n*n g*s e*n:as*ka' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'system:samus ', True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        
    
    def test_predicate_results_cache( self ):
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheInit()
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', False ), False )
        
        #
        
        predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX ) ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheSystem( predicates )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', False ), False )
        
        #
        
        samus = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        #
        
        predicates = [ samus, samus_aran, character_samus_aran ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'samus', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus br', True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus br', False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus*' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samas br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus ar*' ) ), { samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus aran*' ) ), { samus_aran, character_samus_aran } )
        
        #
        
        predicates = [ samus ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'samus', True )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus' ) ), { samus } )
        
        #
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'character:samus', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( '', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'samus ar', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus', False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus ar', True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus ar', False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus br', True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'character:samus br', False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'metroid', False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( 'series:samus', False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
    
    def test_predicate_strings_and_namespaces( self ):
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag' )
        
        self.assertEqual( p.ToString(), 'tag' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag', min_current_count = 1, min_pending_count = 2 )
        
        self.assertEqual( p.ToString( with_count = False ), 'tag' )
        self.assertEqual( p.ToString( with_count = True ), 'tag (1) (+2)' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag', False )
        
        self.assertEqual( p.ToString(), '-tag' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag', False, 1, 2 )
        
        self.assertEqual( p.ToString( with_count = False ), '-tag' )
        self.assertEqual( p.ToString( with_count = True ), '-tag (1) (+2)' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:time imported: since 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '\u2248', 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:time imported: around 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:time imported: before 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE, min_current_count = 1000 )
        
        self.assertEqual( p.ToString(), 'system:archive (1,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '<', 200 ) )
        
        self.assertEqual( p.ToString(), 'system:duration < 200 milliseconds' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, min_current_count = 2000 )
        
        self.assertEqual( p.ToString(), 'system:everything (2,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is currently in my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is not pending to my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True )
        
        self.assertEqual( p.ToString(), 'system:has audio' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, ( ( bytes.fromhex( 'abcd' ), ), 'sha256' ) )
        
        self.assertEqual( p.ToString(), 'system:sha256 hash is abcd' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 2000 ) )
        
        self.assertEqual( p.ToString(), 'system:height < 2,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX, min_current_count = 1000 )
        
        self.assertEqual( p.ToString(), 'system:inbox (1,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 2000 )
        
        self.assertEqual( p.ToString(), 'system:limit is 2,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LOCAL, min_current_count = 100 )
        
        self.assertEqual( p.ToString(), 'system:local (100)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, set( HC.IMAGES ).intersection( HC.SEARCHABLE_MIMES ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is image' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, ( HC.VIDEO_WEBM, ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is webm' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, ( HC.VIDEO_WEBM, HC.IMAGE_GIF ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is webm, gif' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, min_current_count = 100 )
        
        self.assertEqual( p.ToString(), 'system:not local (100)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '<', 2 ) )
        
        self.assertEqual( p.ToString(), 'system:number of tags < 2' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '<', 5000 ) )
        
        self.assertEqual( p.ToString(), 'system:number of words < 5,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.2, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:rating for my files > 0.2' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 16, 9 ) )
        
        self.assertEqual( p.ToString(), 'system:ratio = 16:9' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( ( bytes.fromhex( 'abcd' ), ), 5 ) )
        
        self.assertEqual( p.ToString(), 'system:similar to 1 files using max hamming of 5' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5, 1048576 ) )
        
        self.assertEqual( p.ToString(), 'system:filesize > 5MB' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 1920 ) )
        
        self.assertEqual( p.ToString(), 'system:width = 1,920' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'series' )
        
        self.assertEqual( p.ToString(), 'series:*anything*' )
        self.assertEqual( p.GetNamespace(), 'series' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series', False )
        
        self.assertEqual( p.ToString(), '-series' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'a*i:o*' )
        
        self.assertEqual( p.ToString(), 'a*i:o* (wildcard search)' )
        self.assertEqual( p.GetNamespace(), 'a*i' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'a*i:o*', False )
        
        self.assertEqual( p.ToString(), '-a*i:o*' )
        self.assertEqual( p.GetNamespace(), 'a*i' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'series:game of thrones' )
        
        self.assertEqual( p.ToString(), '    series:game of thrones' )
        self.assertEqual( p.GetNamespace(), 'series' )
        self.assertEqual( p.GetTextsAndNamespaces(), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_OR_CONTAINER, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 2000 ) ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'blue eyes' ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' ) ] )
        
        self.assertEqual( p.ToString(), 'system:height < 2,000 OR blue eyes OR character:samus aran' )
        self.assertEqual( p.GetNamespace(), '' )
        
        or_texts_and_namespaces = []
        
        or_texts_and_namespaces.append( ( 'system:height < 2,000', 'system' ) )
        or_texts_and_namespaces.append( ( ' OR ', 'system' ) )
        or_texts_and_namespaces.append( ( 'blue eyes', '' ) )
        or_texts_and_namespaces.append( ( ' OR ', 'system' ) )
        or_texts_and_namespaces.append( ( 'character:samus aran', 'character' ) )
        
        
        self.assertEqual( p.GetTextsAndNamespaces(), or_texts_and_namespaces )
        
    
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
        
    
class TestTagSiblings( unittest.TestCase ):
    
    @classmethod
    def setUpClass( cls ):
        
        cls._first_key = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
        cls._second_key = HG.test_controller.example_tag_repo_service_key
        
        tag_siblings = collections.defaultdict( HydrusData.default_dict_set )
        
        first_dict = HydrusData.default_dict_set()
        
        first_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'ishygddt', 'i sure hope you guys don\'t do that' ), ( 'character:rei ayanami', 'character:ayanami rei' ), ( 'tree_1', 'tree_3' ), ( 'tree_2', 'tree_3' ), ( 'tree_3', 'tree_5' ), ( 'tree_4', 'tree_5' ), ( 'tree_5', 'tree_6' ), ( 'current_a', 'current_b' ), ( 'chain_a', 'chain_b' ), ( 'chain_b', 'chain_c' ), ( 'closed_loop', 'closed_loop' ), ( 'loop_a', 'loop_b' ), ( 'loop_b', 'loop_c' ), ( 'loop_c', 'loop_a' ) }
        first_dict[ HC.CONTENT_STATUS_DELETED ] = { ( 'deleted_a', 'deleted_b' ) }
        
        second_dict = HydrusData.default_dict_set()
        
        second_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'loop_c', 'loop_a' ), ( 'current_a', 'current_b' ), ( 'petitioned_a', 'petitioned_b' ) }
        second_dict[ HC.CONTENT_STATUS_DELETED ] = { ( 'pending_a', 'pending_b' ) }
        second_dict[ HC.CONTENT_STATUS_PENDING ] = { ( 'pending_a', 'pending_b' ) }
        second_dict[ HC.CONTENT_STATUS_PETITIONED ] = { ( 'petitioned_a', 'petitioned_b' ) }
        
        tag_siblings[ cls._first_key ] = first_dict
        tag_siblings[ cls._second_key ] = second_dict
        
        HG.test_controller.SetRead( 'tag_siblings', tag_siblings )
        
        cls._tag_siblings_manager = ClientManagers.TagSiblingsManager( HG.test_controller )
        
    
    def test_collapse_predicates( self ):
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'chain_a', min_current_count = 10 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'chain_b', min_current_count = 5 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'chain_c', min_current_count = 20 ) )
        
        results = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'chain_c', min_current_count = 20, max_current_count = 35 ) ]
        
        self.assertEqual( self._tag_siblings_manager.CollapsePredicates( self._first_key, predicates ), results )
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'chain_a', min_current_count = 10 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'chain_b', min_current_count = 5 ) )
        predicates.append( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'chain_c', min_current_count = 20 ) )
        
        ( result, ) = self._tag_siblings_manager.CollapsePredicates( self._first_key, predicates )
        
        self.assertEqual( result.GetCount(), 20 )
        self.assertEqual( result.ToString(), 'chain_c (20-35)' )
        
    
    def test_chain( self ):
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'chain_a' ), 'chain_c' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'chain_b' ), 'chain_c' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'chain_c' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'chain_a' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'chain_b' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'chain_c' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'chain_a', 'chain_b' ] ) ), set( [ 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'chain_a', 'chain_b', 'chain_c' ] ) ), set( [ 'chain_c' ] ) )
        
    
    def test_current( self ):
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'current_a' ), 'current_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'current_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'current_a' ) ), set( [ 'current_a', 'current_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'current_b' ) ), set( [ 'current_a', 'current_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'chain_a', 'chain_b' ] ) ), set( [ 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'chain_a', 'chain_b', 'chain_c' ] ) ), set( [ 'chain_c' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'chain_a' : 10, 'chain_b' : 5 } ), { 'chain_c' : 15 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'chain_a' : 10, 'chain_b' : 5, 'chain_c' : 20 } ), { 'chain_c' : 35 } )
        
    
    def test_deleted( self ):
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'deleted_a' ), None )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'deleted_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'deleted_a' ) ), set( [ 'deleted_a' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'deleted_b' ) ), set( [ 'deleted_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'deleted_a', 'deleted_b' ] ) ), set( [ 'deleted_a', 'deleted_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'deleted_a' : 10, 'deleted_b' : 5 } ), { 'deleted_a' : 10, 'deleted_b' : 5 } )
        
    
    def test_no_loop( self ):
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'closed_loop' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'closed_loop' ) ), set( [ 'closed_loop' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'closed_loop' ] ) ), set( [ 'closed_loop' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'closed_loop' : 10 } ), { 'closed_loop' : 10 } )
        
    
    def test_not_exist( self ):
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'not_exist' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'not_exist' ) ), set( [ 'not_exist' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'not_exist' ] ) ), set( [ 'not_exist' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'not_exist' : 10 } ), { 'not_exist' : 10 } )
        
    
    def test_pending_overwrite( self ):
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'pending_a' ), 'pending_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'pending_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'pending_a' ) ), set( [ 'pending_a', 'pending_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'pending_b' ) ), set( [ 'pending_a', 'pending_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'pending_a' ] ) ), set( [ 'pending_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'pending_a', 'pending_b' ] ) ), set( [ 'pending_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'pending_a' : 10 } ), { 'pending_b' : 10 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'pending_a' : 10, 'pending_b' : 5 } ), { 'pending_b' : 15 } )
        
    
    def test_petitioned_no_overwrite( self ):
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'petitioned_a' ), 'petitioned_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'petitioned_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'petitioned_a' ) ), set( [ 'petitioned_a', 'petitioned_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'petitioned_b' ) ), set( [ 'petitioned_a', 'petitioned_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'petitioned_a' ] ) ), set( [ 'petitioned_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'petitioned_a', 'petitioned_b' ] ) ), set( [ 'petitioned_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'petitioned_a' : 10 } ), { 'petitioned_b' : 10 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'petitioned_a' : 10, 'petitioned_b' : 5 } ), { 'petitioned_b' : 15 } )
        
    
    def test_tree( self ):
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'tree_1' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'tree_2' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'tree_3' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'tree_4' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'tree_5' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'tree_6' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'tree_1' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'tree_2' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'tree_3' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'tree_4' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'tree_5' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'tree_6' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'tree_1' ] ) ), set( [ 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'tree_1', 'tree_3', 'tree_5' ] ) ), set( [ 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) ), set( [ 'tree_6' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'tree_1' : 10 } ), { 'tree_6' : 10 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'tree_1' : 10, 'tree_3' : 5, 'tree_5' : 20 } ), { 'tree_6' : 35 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'tree_1' : 10, 'tree_2' : 3, 'tree_3' : 5, 'tree_4' : 2, 'tree_5' : 20, 'tree_6' : 30 } ), { 'tree_6' : 70 } )
        
    
