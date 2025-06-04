import collections
import collections.abc
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusTags

from hydrus.client import ClientConstants as CC
from hydrus.client.media import ClientMediaManagers
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.metadata import ClientTagsHandling
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import TestGlobals as TG

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
        
        self.assertEqual( tags_manager.GetNamespaceSlice( CC.COMBINED_TAG_SERVICE_KEY, ( 'character', ), ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ), frozenset( { 'character:cibo' } ) )
        
    

class TestTagsManager( unittest.TestCase ):
    
    _first_key: bytes = HydrusData.GenerateKey()
    _second_key: bytes = HydrusData.GenerateKey()
    _third_key: bytes = HydrusData.GenerateKey()
    
    _pending_service_key: bytes = HydrusData.GenerateKey()
    _content_update_service_key: bytes = HydrusData.GenerateKey()
    _reset_service_key: bytes = HydrusData.GenerateKey()
    
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
        
        self.assertEqual( self._tags_manager.GetNamespaceSlice( CC.COMBINED_TAG_SERVICE_KEY, ( 'creator', 'series' ), ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ), frozenset( { 'creator:tsutomu nihei', 'series:blame!' } ) )
        self.assertEqual( self._tags_manager.GetNamespaceSlice( CC.COMBINED_TAG_SERVICE_KEY, [], ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL ), frozenset() )
        
    
    def test_get_num_tags( self ):
        
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._first_key, include_current_tags = False, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._first_key, include_current_tags = True, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 8 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._first_key, include_current_tags = False, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._first_key, include_current_tags = True, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 8 )
        
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._second_key, include_current_tags = False, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._second_key, include_current_tags = True, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 2 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._second_key, include_current_tags = False, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._second_key, include_current_tags = True, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 3 )
        
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._third_key, include_current_tags = False, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._third_key, include_current_tags = True, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._third_key, include_current_tags = False, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = self._third_key, include_current_tags = True, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 1 )
        
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = False, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = False ), ClientTags.TAG_DISPLAY_STORAGE ), 10 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = False, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( ClientSearchTagContext.TagContext( service_key = CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True ), ClientTags.TAG_DISPLAY_STORAGE ), 11 )
        
    
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
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'hello', hashes ), reason = 'reason' )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'hello', hashes ), reason = 'reason' )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key, ClientTags.TAG_DISPLAY_STORAGE ), { 'hello' } )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending( CC.COMBINED_TAG_SERVICE_KEY, ClientTags.TAG_DISPLAY_STORAGE ) )
        
        #
        
        content_update = ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'hello', hashes ) )
        
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
        
    

class TestTagRendering( unittest.TestCase ):
    
    def test_rendering( self ):
        
        self.assertEqual( ClientTags.RenderTag( 'tag', True ), 'tag' )
        self.assertEqual( ClientTags.RenderTag( 'test_tag', True ), 'test_tag' )
        
        TG.test_controller.new_options.SetBoolean( 'replace_tag_underscores_with_spaces', True )
        
        self.assertEqual( ClientTags.RenderTag( 'test_tag', True ), 'test tag' )
        
        TG.test_controller.new_options.SetBoolean( 'replace_tag_underscores_with_spaces', False )
        
        TG.test_controller.new_options.SetBoolean( 'replace_tag_emojis_with_boxes', True )
        
        self.assertEqual( ClientTags.RenderTag( 'title:skeb⛓️💙', True ), 'title:skeb□□' )
        
        TG.test_controller.new_options.SetBoolean( 'replace_tag_emojis_with_boxes', False )
        
        self.assertEqual( ClientTags.RenderTag( 'character:lara', True ), 'character:lara' )
        
        TG.test_controller.new_options.SetBoolean( 'show_namespaces', False )
        
        self.assertEqual( ClientTags.RenderTag( 'character:lara', True ), 'lara' )
        
        TG.test_controller.new_options.SetBoolean( 'show_namespaces', True )
        
    
