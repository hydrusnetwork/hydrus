import collections
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.external import SystemPredicateParser

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientManagers
from hydrus.client import ClientSearch
from hydrus.client import ClientSearchParseSystemPredicates
from hydrus.client.media import ClientMediaManagers
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagsHandling

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
        
        service_keys_to_statuses_to_display_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_display_tags[ first ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_1', 'series:blame!' }
        
        service_keys_to_statuses_to_display_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate_1', 'character:cibo' }
        service_keys_to_statuses_to_display_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'pending_1', 'creator:tsutomu nihei' }
        
        service_keys_to_statuses_to_display_tags[ third ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate', 'current_duplicate_1' }
        service_keys_to_statuses_to_display_tags[ third ][ HC.CONTENT_STATUS_PENDING ] = { 'volume:3' }
        
        tags_manager_1 = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
        
        #
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ first ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_2', 'series:blame!', 'chapter:1' }
        service_keys_to_statuses_to_tags[ first ][ HC.CONTENT_STATUS_DELETED ] = { 'deleted_2' }
        
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate'  }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'architecture', 'chapter:2' }
        
        service_keys_to_statuses_to_tags[ third ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate' }
        
        service_keys_to_statuses_to_display_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_display_tags[ first ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_2', 'series:blame!', 'chapter:1' }
        service_keys_to_statuses_to_display_tags[ first ][ HC.CONTENT_STATUS_DELETED ] = { 'deleted_2' }
        
        service_keys_to_statuses_to_display_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate'  }
        service_keys_to_statuses_to_display_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'architecture', 'chapter:2' }
        
        service_keys_to_statuses_to_display_tags[ third ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate' }
        
        tags_manager_2 = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
        
        #
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'page:4', 'page:5' }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'title:double page spread' }
        
        service_keys_to_statuses_to_display_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_display_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'page:4', 'page:5' }
        service_keys_to_statuses_to_display_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'title:double page spread' }
        
        tags_manager_3 = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
        
        #
        
        tags_managers = ( tags_manager_1, tags_manager_2, tags_manager_3 )
        
        tags_manager = ClientMediaManagers.TagsManager.MergeTagsManagers( tags_managers )
        
        #
        
        self.assertEqual( tags_manager.GetNamespaceSlice( ( 'character', ), ClientTags.TAG_DISPLAY_ACTUAL ), frozenset( { 'character:cibo' } ) )
        
    
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
        
        service_keys_to_statuses_to_display_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_display_tags[ cls._first_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'current', '\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1' }
        service_keys_to_statuses_to_display_tags[ cls._first_key ][ HC.CONTENT_STATUS_DELETED ] = { 'deleted' }
        
        service_keys_to_statuses_to_display_tags[ cls._second_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'deleted', '\u2835' }
        service_keys_to_statuses_to_display_tags[ cls._second_key ][ HC.CONTENT_STATUS_PENDING ] = { 'pending' }
        
        service_keys_to_statuses_to_display_tags[ cls._third_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'petitioned' }
        service_keys_to_statuses_to_display_tags[ cls._third_key ][ HC.CONTENT_STATUS_DELETED ] = { 'pending' }
        
        cls._tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
        
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
        
        other_service_keys_to_statuses_to_display_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        other_service_keys_to_statuses_to_display_tags[ cls._pending_service_key ][ HC.CONTENT_STATUS_PENDING ] = { 'pending' }
        
        other_service_keys_to_statuses_to_display_tags[ cls._reset_service_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'reset_current' }
        other_service_keys_to_statuses_to_display_tags[ cls._reset_service_key ][ HC.CONTENT_STATUS_PENDING ] = { 'reset_pending' }
        
        cls._other_tags_manager = ClientMediaManagers.TagsManager( other_service_keys_to_statuses_to_tags, other_service_keys_to_statuses_to_display_tags )
        
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
        
        self.assertEqual( self._tags_manager.GetNamespaceSlice( ( 'creator', 'series' ), ClientTags.TAG_DISPLAY_ACTUAL ), frozenset( { 'creator:tsutomu nihei', 'series:blame!' } ) )
        self.assertEqual( self._tags_manager.GetNamespaceSlice( [], ClientTags.TAG_DISPLAY_ACTUAL ), frozenset() )
        
    
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
        
        filter_pages = HydrusTags.TagFilter()
        
        filter_pages.SetRule( 'page:', HC.FILTER_BLACKLIST )
        
        tag_display_manager = ClientTagsHandling.TagDisplayManager()
        
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
            
            self.assertEqual( pat.IsAcceptableForFileSearches(), values[0] )
            self.assertEqual( pat.IsAcceptableForTagSearches(), values[1] )
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
            
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ '', '' ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        search_text_tests( parsed_autocomplete_text, [ '', '' ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, False ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus', inclusive = False ), [] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'samus*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus*', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'samus*' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'samus*' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'character:samus ', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'character:samus', 'character:samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-character:samus ', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, False ] )
        search_text_tests( parsed_autocomplete_text, [ 'character:samus', 'character:samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus', inclusive = False ), [] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 's*s', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s', 's*s*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s*' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s*' ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-s*s', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, False ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s', 's*s*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s*', inclusive = False ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s*', inclusive = False ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s', inclusive = False ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'metroid:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'metroid' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'metroid' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-metroid:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, False ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'metroid', inclusive = False ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'metroid', inclusive = False ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 's*s a*n', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 's*s a*n', 's*s a*n*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s a*n*' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s a*n*' ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 's*s a*n' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( ' samus ', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '[samus]', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, '[samus]' ), [] ] )
        write_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, '[samus]' ) ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'creator-id:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'creator-id' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'creator-id' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'creator-id:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, True, True, False, True ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'creator-id' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'creator-id' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'n*n g*s e*n:as*ka', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, False, False, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'n*n g*s e*n:as*ka', 'n*n g*s e*n:as*ka*' ] )
        read_predicate_tests( parsed_autocomplete_text, [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'n*n g*s e*n:as*ka*' ), [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'n*n g*s e*n:as*ka*' ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'n*n g*s e*n:as*ka' ) ] ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'system:samus ', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        search_text_tests( parsed_autocomplete_text, [ 'samus', 'samus*' ] )
        
        #
        #
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = True
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '*:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'series:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, True, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'series:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, True, False, True ] )
        
        #
        #
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = True
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '*:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'series:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, True, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'series:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, True, False, True ] )
        
        #
        #
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = True
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '*:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'series:', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, False, False, False, True, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'series:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, True, False, True ] )
        
        #
        #
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = True
        fetch_all_allowed = True
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, True, False, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '-', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, False, False, False, False, False, False ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, False, False, True, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, True, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( '*:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ False, True, False, True, False, False, True ] )
        
        #
        
        parsed_autocomplete_text = ClientSearch.ParsedAutocompleteText( 'series:*', tag_autocomplete_options, True )
        
        bool_tests( parsed_autocomplete_text, [ True, True, False, True, True, False, True ] )
        
    
    def test_predicate_results_cache_init( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheInit()
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
    
    def test_predicate_results_cache_system( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        predicates = [ ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX ) ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheSystem( predicates )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
    
    def test_predicate_results_cache_subtag_normal( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        #
        
        predicates = [ samus, samus_aran, character_samus_aran ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'samus', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus*' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samas br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus ar*' ) ), { samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus aran*' ) ), { samus_aran, character_samus_aran } )
        
    
    def test_predicate_results_cache_subtag_exact( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ samus ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'samus', True )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus' ) ), { samus } )
        
    
    def test_predicate_results_cache_full_normal( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'character:samus', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'characte:samus aran*' ) ), set() )
        
    
    def test_predicate_results_cache_namespace_explicit_fetch_all( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'character:*', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        #
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = True
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
    
    def test_predicate_results_cache_namespace_bare_fetch_all( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'character:', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        #
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = True
        namespace_fetch_all_allowed = True
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
    
    def test_predicate_results_cache_namespaces_into_full_tags( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ character_samus_aran ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, 'char', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        #
        
        search_namespaces_into_full_tags = True
        namespace_bare_fetch_all_allowed = True
        namespace_fetch_all_allowed = True
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
    
    def test_predicate_results_cache_fetch_all_madness( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        search_namespaces_into_full_tags = False
        namespace_bare_fetch_all_allowed = False
        namespace_fetch_all_allowed = False
        fetch_all_allowed = False
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        samus = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus' )
        samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'samus aran' )
        character_samus_aran = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'character:samus aran' )
        
        predicates = [ samus, samus_aran, character_samus_aran ]
        
        predicate_results_cache = ClientSearch.PredicateResultsCacheTag( predicates, '*', False )
        
        self.assertEqual( predicate_results_cache.GetPredicates(), predicates )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), False )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), False )
        
        #
        
        search_namespaces_into_full_tags = True
        namespace_bare_fetch_all_allowed = True
        namespace_fetch_all_allowed = True
        fetch_all_allowed = True
        
        tag_autocomplete_options.SetTuple(
            tag_autocomplete_options.GetWriteAutocompleteTagDomain(),
            tag_autocomplete_options.OverridesWriteAutocompleteFileDomain(),
            tag_autocomplete_options.GetWriteAutocompleteFileDomain(),
            search_namespaces_into_full_tags,
            namespace_bare_fetch_all_allowed,
            namespace_fetch_all_allowed,
            fetch_all_allowed
        )
        
        pat_empty = ClientSearch.ParsedAutocompleteText( '', tag_autocomplete_options, True )
        pat_samus = ClientSearch.ParsedAutocompleteText( 'samus', tag_autocomplete_options, True )
        pat_samus_ar = ClientSearch.ParsedAutocompleteText( 'samus ar', tag_autocomplete_options, True )
        pat_samus_br = ClientSearch.ParsedAutocompleteText( 'samus br', tag_autocomplete_options, True )
        pat_character_samus = ClientSearch.ParsedAutocompleteText( 'character:samus', tag_autocomplete_options, True )
        pat_character_samus_ar = ClientSearch.ParsedAutocompleteText( 'character:samus ar', tag_autocomplete_options, True )
        pat_character_samus_br = ClientSearch.ParsedAutocompleteText( 'character:samus br', tag_autocomplete_options, True )
        pat_metroid = ClientSearch.ParsedAutocompleteText( 'metroid', tag_autocomplete_options, True )
        pat_series_samus = ClientSearch.ParsedAutocompleteText( 'series:samus', tag_autocomplete_options, True )
        
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_empty, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_ar, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_character_samus_br, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_metroid, False ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, True ), True )
        self.assertEqual( predicate_results_cache.CanServeTagResults( pat_series_samus, False ), True )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus ar*' ) ), { character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'character:samus aran*' ) ), { character_samus_aran } )
        
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus*' ) ), { samus, samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samas br*' ) ), set() )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus ar*' ) ), { samus_aran, character_samus_aran } )
        self.assertEqual( set( predicate_results_cache.FilterPredicates( CC.COMBINED_TAG_SERVICE_KEY, 'samus aran*' ) ), { samus_aran, character_samus_aran } )
        
    
    def test_predicate_counts( self ):
        
        # quick test for counts and __hash__
        
        p_c = ClientSearch.PredicateCount( 1, 2, 3, 4 )
        
        self.assertEqual( p_c.min_current_count, 1 )
        self.assertEqual( p_c.min_pending_count, 2 )
        self.assertEqual( p_c.max_current_count, 3 )
        self.assertEqual( p_c.max_pending_count, 4 )
        
        self.assertNotEqual( p_c, ClientSearch.PredicateCount( 1, 2, 3, 5 ) )
        self.assertNotEqual( p_c, ClientSearch.PredicateCount( 1, 5, 3, 4 ) )
        self.assertEqual( p_c, ClientSearch.PredicateCount( 1, 2, 3, 4 ) )
        
        #
        
        null = ClientSearch.PredicateCount.STATICCreateNullCount()
        
        self.assertEqual( null, ClientSearch.PredicateCount( 0, 0, 0, 0 ) )
        self.assertEqual( null.GetMinCount(), 0 )
        self.assertEqual( null.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 0 )
        self.assertEqual( null.GetMinCount( HC.CONTENT_STATUS_PENDING ), 0 )
        self.assertEqual( null.HasZeroCount(), True )
        self.assertEqual( null.HasNonZeroCount(), False )
        self.assertEqual( null.GetSuffixString(), '' )
        
        #
        
        p_c = ClientSearch.PredicateCount( 3, 0, 3, 0 )
        
        self.assertEqual( p_c, ClientSearch.PredicateCount( 3, 0, 3, 0 ) )
        self.assertEqual( p_c.GetMinCount(), 3 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 3 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 0 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(3)' )
        
        #
        
        p_c = ClientSearch.PredicateCount( 0, 5, 0, 5 )
        
        self.assertEqual( p_c, ClientSearch.PredicateCount( 0, 5, 0, 5 ) )
        self.assertEqual( p_c.GetMinCount(), 5 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 0 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 5 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(+5)' )
        
        #
        
        p_c = ClientSearch.PredicateCount( 100, 0, 150, 0 )
        
        self.assertEqual( p_c, ClientSearch.PredicateCount( 100, 0, 150, 0 ) )
        self.assertEqual( p_c.GetMinCount(), 100 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 100 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 0 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(100-150)' )
        
        #
        
        p_c = ClientSearch.PredicateCount( 0, 80, 0, 85 )
        
        self.assertEqual( p_c, ClientSearch.PredicateCount( 0, 80, 0, 85 ) )
        self.assertEqual( p_c.GetMinCount(), 80 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 0 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 80 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(+80-85)' )
        
        #
        
        p_c = ClientSearch.PredicateCount( 0, 0, 1500, 0 )
        
        self.assertEqual( p_c, ClientSearch.PredicateCount( 0, 0, 1500, 0 ) )
        self.assertEqual( p_c.GetMinCount(), 0 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 0 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 0 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(0-1,500)' )
        
        #
        
        p_c = ClientSearch.PredicateCount( 1, 2, 3, 4 )
        
        self.assertEqual( p_c, ClientSearch.PredicateCount( 1, 2, 3, 4 ) )
        self.assertEqual( p_c.GetMinCount(), 3 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_CURRENT ), 1 )
        self.assertEqual( p_c.GetMinCount( HC.CONTENT_STATUS_PENDING ), 2 )
        self.assertEqual( p_c.HasZeroCount(), False )
        self.assertEqual( p_c.HasNonZeroCount(), True )
        self.assertEqual( p_c.GetSuffixString(), '(1-3) (+2-4)' )
        
        #
        
        p_c_1 = ClientSearch.PredicateCount( 10, 2, 12, 4 )
        p_c_2 = ClientSearch.PredicateCount( 1, 0, 2, 4 )
        
        p_c_1.AddCounts( p_c_2 )
        
        self.assertEqual( p_c_1, ClientSearch.PredicateCount( 10, 2, 14, 8 ) )
        
    
    def test_predicate_strings_and_namespaces( self ):
        
        render_for_user = False
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag' )
        
        self.assertEqual( p.ToString(), 'tag' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag', True, count = ClientSearch.PredicateCount.STATICCreateStaticCount( 1, 2 ) )
        
        self.assertEqual( p.ToString( with_count = False ), 'tag' )
        self.assertEqual( p.ToString( with_count = True ), 'tag (1) (+2)' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag', False )
        
        self.assertEqual( p.ToString(), '-tag' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'tag', False, count = ClientSearch.PredicateCount.STATICCreateStaticCount( 1, 2 ) )
        
        self.assertEqual( p.ToString( with_count = False ), '-tag' )
        self.assertEqual( p.ToString( with_count = True ), '-tag (1) (+2)' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:import time: since 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( CC.UNICODE_ALMOST_EQUAL_TO, 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:import time: around 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 'delta', ( 1, 2, 3, 4 ) ) )
        
        self.assertEqual( p.ToString(), 'system:import time: before 1 year 2 months ago' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( 1000 ) )
        
        self.assertEqual( p.ToString(), 'system:archive (1,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ( '<', 200 ) )
        
        self.assertEqual( p.ToString(), 'system:duration < 200 milliseconds' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_EVERYTHING, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( 2000 ) )
        
        self.assertEqual( p.ToString(), 'system:everything (2,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is currently in my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_DELETED, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is deleted from my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is not pending to my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PETITIONED, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:is not petitioned from my files' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True )
        
        self.assertEqual( p.ToString(), 'system:has audio' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False )
        
        self.assertEqual( p.ToString(), 'system:no audio' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, True )
        
        self.assertEqual( p.ToString(), 'system:has icc profile' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, False )
        
        self.assertEqual( p.ToString(), 'system:no icc profile' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HASH, ( ( bytes.fromhex( 'abcd' ), ), 'sha256' ) )
        
        self.assertEqual( p.ToString(), 'system:sha256 hash is abcd' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 2000 ) )
        
        self.assertEqual( p.ToString(), 'system:height < 2,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( 1000 ) )
        
        self.assertEqual( p.ToString(), 'system:inbox (1,000)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 2000 )
        
        self.assertEqual( p.ToString(), 'system:limit is 2,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LOCAL, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( 100 ) )
        
        self.assertEqual( p.ToString(), 'system:local (100)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, set( HC.IMAGES ).intersection( HC.SEARCHABLE_MIMES ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is image' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, ( HC.VIDEO_WEBM, ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is webm' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MIME, ( HC.VIDEO_WEBM, HC.IMAGE_GIF ) )
        
        self.assertEqual( p.ToString(), 'system:filetype is webm, gif' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, count = ClientSearch.PredicateCount.STATICCreateCurrentCount( 100 ) )
        
        self.assertEqual( p.ToString(), 'system:not local (100)' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( None, '<', 2 ) )
        
        self.assertEqual( p.ToString(), 'system:number of tags < 2' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( 'character', '<', 2 ) )
        
        self.assertEqual( p.ToString(), 'system:number of character tags < 2' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '<', 5000 ) )
        
        self.assertEqual( p.ToString(), 'system:number of words < 5,000' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        from hydrus.test import TestController
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.2, TestController.LOCAL_RATING_NUMERICAL_SERVICE_KEY ) )
        
        self.assertEqual( p.ToString(), 'system:rating for example local rating numerical service > 1/5' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 16, 9 ) )
        
        self.assertEqual( p.ToString(), 'system:ratio = 16:9' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( ( bytes.fromhex( 'abcd' ), ), 5 ) )
        
        self.assertEqual( p.ToString(), 'system:similar to 1 files using max hamming of 5' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5, 1048576 ) )
        
        self.assertEqual( p.ToString(), 'system:filesize > 5MB' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 1920 ) )
        
        self.assertEqual( p.ToString(), 'system:width = 1,920' )
        self.assertEqual( p.GetNamespace(), 'system' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_NAMESPACE, 'series' )
        
        self.assertEqual( p.ToString(), 'series:*anything*' )
        self.assertEqual( p.GetNamespace(), 'series' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'series', False )
        
        self.assertEqual( p.ToString(), '-series' )
        self.assertEqual( p.GetNamespace(), '' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_WILDCARD, 'a*i:o*' )
        
        self.assertEqual( p.ToString(), 'a*i:o* (wildcard search)' )
        self.assertEqual( p.GetNamespace(), 'a*i' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, 'a*i:o*', False )
        
        self.assertEqual( p.ToString(), '-a*i:o*' )
        self.assertEqual( p.GetNamespace(), 'a*i' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
        #
        
        p = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_PARENT, 'series:game of thrones' )
        
        self.assertEqual( p.ToString(), '    series:game of thrones' )
        self.assertEqual( p.GetNamespace(), 'series' )
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), [ ( p.ToString(), p.GetNamespace() ) ] )
        
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
        
        
        self.assertEqual( p.GetTextsAndNamespaces( render_for_user ), or_texts_and_namespaces )
        
    
    def test_system_predicate_parsing( self ):
        
        for ( expected_result_text, sys_pred_text ) in [
            ( 'system:everything', "system:everything" ),
            ( 'system:inbox', "system:inbox  " ),
            ( 'system:archive', "system:archive " ),
            ( 'system:has duration', "system:has duration" ),
            ( 'system:has duration', "system:has_duration" ),
            ( 'system:no duration', "   system:no_duration" ),
            ( 'system:no duration', "system:no duration" ),
            ( 'system:is the best quality file of its duplicate group', "system:is the best quality file  of its group" ),
            ( 'system:is not the best quality file of its duplicate group', "system:isn't the best quality file of its duplicate group" ),
            ( 'system:is not the best quality file of its duplicate group', 'system:is not the best quality file of its duplicate group' ),
            ( 'system:has audio', "system:has_audio" ),
            ( 'system:no audio', "system:no audio" ),
            ( 'system:has tags', "system:has tags" ),
            ( 'system:untagged', "system:no tags" ),
            ( 'system:untagged', "system:untagged" ),
            ( 'system:number of tags > 5', "system:number of tags > 5" ),
            ( 'system:number of tags \u2248 10', "system:number of tags ~= 10" ),
            ( 'system:has tags', "system:number of tags > 0  " ),
            ( 'system:number of words < 2', "system:number of words < 2" ),
            ( 'system:height = 600', "system:height = 600px" ),
            ( 'system:height = 800', "system:height is 800" ),
            ( 'system:height > 900', "system:height > 900" ),
            ( 'system:width < 200', "system:width < 200" ),
            ( 'system:width > 1,000', "system:width > 1000 pixels" ),
            ( 'system:filesize \u2248 50KB', "system:filesize ~= 50 kilobytes" ),
            ( 'system:filesize > 10MB', "system:filesize > 10megabytes" ),
            ( 'system:filesize < 1GB', "system:file size    < 1 GB" ),
            ( 'system:filesize > 0B', "system:file size > 0 B" ),
            ( 'system:similar to 4 files using max hamming of 3', "system:similar to abcdef01 abcdef02 abcdef03, abcdef04 with distance 3" ),
            ( 'system:similar to 1 files using max hamming of 5', "system:similar to abcdef distance 5" ),
            ( 'system:limit is 5,000', "system:limit is 5000" ),
            ( 'system:limit is 100', "system:limit = 100" ),
            ( 'system:filetype is jpeg', "system:filetype is jpeg" ),
            ( 'system:filetype is jpeg, png, apng', "system:filetype =   image/jpg, image/png, apng" ),
            ( 'system:sha256 hash is in 3 hashes', "system:hash = abcdef01 abcdef02 abcdef03" ),
            ( 'system:md5 hash is in 3 hashes', "system:hash = abcdef01 abcdef, abcdef04 md5" ),
            ( 'system:md5 hash is abcdef01', "system:hash = abcdef01 md5" ),
            ( 'system:md5 hash is abcdef01', "system:Hash = Abcdef01 md5" ),
            ( 'system:sha256 hash is abcdef0102', "system:hash = abcdef0102" ),
            ( 'system:modified time: since 7 years 1 month ago', "system:modified date < 7  years 45 days 70h" ),
            ( 'system:modified time: since 2011-06-04', "system:modified date > 2011-06-04" ),
            ( 'system:modified time: before 7 years 2 months ago', "system:date modified > 7 years 2    months" ),
            ( 'system:modified time: since 1 day ago', "system:date modified < 1 day" ),
            ( 'system:modified time: since 1 month 1 day ago', "system:date modified < 0 years 1 month 1 day 1 hour" ),
            ( 'system:last view time: since 7 years 1 month ago', "system:last viewed time < 7 years 45 days 70h" ),
            ( 'system:last view time: since 7 years 1 month ago', "system:last view time < 7 years 45 days 70h" ),
            ( 'system:import time: since 7 years 1 month ago', "system:time_imported < 7 years 45 days 70h" ),
            ( 'system:import time: since 2011-06-04', "system:time imported > 2011-06-04" ),
            ( 'system:import time: before 7 years 2 months ago', "system:time imported > 7 years 2 months" ),
            ( 'system:import time: since 1 day ago', "system:time imported < 1 day" ),
            ( 'system:import time: since 1 month 1 day ago', "system:time imported < 0 years 1 month 1 day 1 hour" ),
            ( 'system:import time: a month either side of 2011-01-03', " system:time imported ~= 2011-1-3 " ),
            ( 'system:import time: a month either side of 1996-05-02', "system:time imported ~= 1996-05-2" ),
            ( 'system:import time: since 7 years 1 month ago', "system:import_time < 7 years 45 days 70h" ),
            ( 'system:import time: since 2011-06-04', "system:import time > 2011-06-04" ),
            ( 'system:import time: before 7 years 2 months ago', "system:import time > 7 years 2 months" ),
            ( 'system:import time: since 1 day ago', "system:import time < 1 day" ),
            ( 'system:import time: since 1 month 1 day ago', "system:import time < 0 years 1 month 1 day 1 hour" ),
            ( 'system:import time: a month either side of 2011-01-03', " system:import time ~= 2011-1-3 " ),
            ( 'system:import time: a month either side of 1996-05-02', "system:import time ~= 1996-05-2" ),
            ( 'system:duration < 5.0 seconds', "system:duration < 5 seconds" ),
            ( 'system:duration \u2248 11.0 seconds', "system:duration ~= 5 sec 6000 msecs" ),
            ( 'system:duration > 3 milliseconds', "system:duration > 3 milliseconds" ),
            ( 'system:is pending to my files', "system:file service is pending to my files" ),
            ( 'system:is currently in my files', "   system:file service currently in my files" ),
            ( 'system:is not currently in my files', "system:file service isn't currently in my files" ),
            ( 'system:is not pending to my files', "system:file service is not pending to my files" ),
            ( 'system:num file relationships - has less than 3 alternates', "system:num file relationships < 3 alternates" ),
            ( 'system:num file relationships - has more than 3 not related/false positive', "system:number of file relationships > 3 false positives" ),
            ( 'system:ratio wider than 16:9', "system:ratio is wider than 16:9        " ),
            ( 'system:ratio = 16:9', "system:ratio is 16:9" ),
            ( 'system:ratio taller than 1:1', "system:ratio taller than 1:1" ),
            ( 'system:number of pixels > 50 pixels', "system:num pixels > 50 px" ),
            ( 'system:number of pixels < 1 megapixels', "system:num pixels < 1 megapixels " ),
            ( 'system:number of pixels \u2248 5 kilopixels', "system:num pixels ~= 5 kilopixel" ),
            ( 'system:media views \u2248 10', "system:media views ~= 10" ),
            ( 'system:all views > 0', "system:all views > 0" ),
            ( 'system:preview views < 10', "system:preview views < 10  " ),
            ( 'system:media viewtime < 1 day 1 hour', "system:media viewtime < 1 days 1 hour 0 minutes" ),
            ( 'system:all viewtime > 1 hour 1 minute', "system:all viewtime > 1 hours 100 seconds" ),
            ( 'system:preview viewtime \u2248 2 days 7 hours', "system:preview viewtime ~= 1 day 30 hours 100 minutes 90s" ),
            ( 'system:has a url matching regex: index\\.php', " system:has url matching regex index\\.php" ),
            ( 'system:does not have a url matching regex: index\\.php', "system:does not have a url matching regex index\\.php" ),
            ( 'system:has url: https://safebooru.donmai.us/posts/4695284', "system:has_url https://safebooru.donmai.us/posts/4695284" ),
            ( 'system:does not have url: https://safebooru.donmai.us/posts/4695284', " system:doesn't have url https://safebooru.donmai.us/posts/4695284  " ),
            ( 'system:has a url with domain: safebooru.com', "system:has domain safebooru.com" ),
            ( 'system:does not have a url with domain: safebooru.com', "system:doesn't have domain safebooru.com" ),
            ( 'system:has safebooru file page url', "system:has a url with class safebooru file page" ),
            ( 'system:does not have safebooru file page url', "system:doesn't have a url with url class safebooru file page " ),
            ( 'system:page less than 5', "system:tag as number page < 5" )
        ]:
            
            ( sys_pred, ) = ClientSearchParseSystemPredicates.ParseSystemPredicateStringsToPredicates( ( sys_pred_text, ) )
            
            self.assertEqual( sys_pred.ToString(), expected_result_text )
            
        
    
    def test_tag_import_options_simple( self ):
        
        tag_autocomplete_options = ClientTagsHandling.TagAutocompleteOptions( CC.COMBINED_TAG_SERVICE_KEY )
        
        self.assertTrue( tag_autocomplete_options.FetchResultsAutomatically() )
        self.assertEqual( tag_autocomplete_options.GetExactMatchCharacterThreshold(), 2 )
        
        #
        
        tag_autocomplete_options.SetFetchResultsAutomatically( False )
        
        self.assertFalse( tag_autocomplete_options.FetchResultsAutomatically() )
        
        tag_autocomplete_options.SetFetchResultsAutomatically( True )
        
        self.assertTrue( tag_autocomplete_options.FetchResultsAutomatically() )
        
        tag_autocomplete_options.SetExactMatchCharacterThreshold( None )
        
        self.assertEqual( tag_autocomplete_options.GetExactMatchCharacterThreshold(), None )
        
        tag_autocomplete_options.SetExactMatchCharacterThreshold( 2 )
        
        self.assertEqual( tag_autocomplete_options.GetExactMatchCharacterThreshold(), 2 )
        
