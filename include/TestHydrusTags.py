import collections
import HydrusConstants as HC
import HydrusTags
import os
import TestConstants
import unittest
import HydrusData
import ClientCaches
import ClientConstants as CC
import ClientData
import ClientMedia
import ClientSearch
import HydrusGlobals

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
        
        tags_manager_1 = ClientMedia.TagsManager( service_keys_to_statuses_to_tags )
        
        #
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ first ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_2', 'series:blame!', 'chapter:1' }
        service_keys_to_statuses_to_tags[ first ][ HC.CONTENT_STATUS_DELETED ] = { 'deleted_2' }
        
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate'  }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'architecture', 'chapter:2' }
        
        service_keys_to_statuses_to_tags[ third ][ HC.CONTENT_STATUS_CURRENT ] = { 'current_duplicate' }
        
        tags_manager_2 = ClientMedia.TagsManager( service_keys_to_statuses_to_tags )
        
        #
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_CURRENT ] = { 'page:4', 'page:5' }
        service_keys_to_statuses_to_tags[ second ][ HC.CONTENT_STATUS_PENDING ] = { 'title:double page spread' }
        
        tags_manager_3 = ClientMedia.TagsManager( service_keys_to_statuses_to_tags )
        
        #
        
        tags_managers = ( tags_manager_1, tags_manager_2, tags_manager_3 )
        
        tags_manager = ClientMedia.MergeTagsManagers( tags_managers )
        
        #
        
        result = { 'creator' : { 'tsutomu nihei' }, 'series' : { 'blame!' }, 'title' : { 'double page spread' }, 'volume' : { '3' }, 'chapter' : { '1', '2' }, 'page' : { '4', '5' } }
        
        self.assertEqual( tags_manager.GetCombinedNamespaces( ( 'creator', 'series', 'title', 'volume', 'chapter', 'page' ) ), result )
        
        self.assertEqual( tags_manager.GetNamespaceSlice( ( 'character', ) ), frozenset( { 'character:cibo' } ) )
        
    
class TestTagsManager( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._first_key = HydrusData.GenerateKey()
        self._second_key = HydrusData.GenerateKey()
        self._third_key = HydrusData.GenerateKey()
        
        service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        service_keys_to_statuses_to_tags[ self._first_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'current', u'\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1' }
        service_keys_to_statuses_to_tags[ self._first_key ][ HC.CONTENT_STATUS_DELETED ] = { 'deleted' }
        
        service_keys_to_statuses_to_tags[ self._second_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'deleted', u'\u2835' }
        service_keys_to_statuses_to_tags[ self._second_key ][ HC.CONTENT_STATUS_DELETED ] = { 'current' }
        service_keys_to_statuses_to_tags[ self._second_key ][ HC.CONTENT_STATUS_PENDING ] = { 'pending' }
        service_keys_to_statuses_to_tags[ self._second_key ][ HC.CONTENT_STATUS_PETITIONED ] = { 'petitioned' }
        
        service_keys_to_statuses_to_tags[ self._third_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'petitioned' }
        service_keys_to_statuses_to_tags[ self._third_key ][ HC.CONTENT_STATUS_DELETED ] = { 'pending' }
        
        self._tags_manager = ClientMedia.TagsManager( service_keys_to_statuses_to_tags )
        
        self._service_keys_to_statuses_to_tags = service_keys_to_statuses_to_tags
        
        #
        
        self._pending_service_key = HydrusData.GenerateKey()
        self._content_update_service_key = HydrusData.GenerateKey()
        self._reset_service_key = HydrusData.GenerateKey()
        
        other_service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
        
        other_service_keys_to_statuses_to_tags[ self._pending_service_key ][ HC.CONTENT_STATUS_PENDING ] = { 'pending' }
        other_service_keys_to_statuses_to_tags[ self._pending_service_key ][ HC.CONTENT_STATUS_PETITIONED ] = { 'petitioned' }
        
        other_service_keys_to_statuses_to_tags[ self._reset_service_key ][ HC.CONTENT_STATUS_CURRENT ] = { 'reset_current' }
        other_service_keys_to_statuses_to_tags[ self._reset_service_key ][ HC.CONTENT_STATUS_DELETED ] = { 'reset_deleted' }
        other_service_keys_to_statuses_to_tags[ self._reset_service_key ][ HC.CONTENT_STATUS_PENDING ] = { 'reset_pending' }
        other_service_keys_to_statuses_to_tags[ self._reset_service_key ][ HC.CONTENT_STATUS_PETITIONED ] = { 'reset_petitioned' }
        
        self._other_tags_manager = ClientMedia.TagsManager( other_service_keys_to_statuses_to_tags )
        
        self._other_service_keys_to_statuses_to_tags = other_service_keys_to_statuses_to_tags
        
    
    def test_get_cstvcp( self ):
        
        result = { 'creator' : { 'tsutomu nihei' }, 'series' : { 'blame!' }, 'title' : { 'test title' }, 'volume' : { '3' }, 'chapter' : { '2' }, 'page' : { '1' } }
        
        self.assertEqual( self._tags_manager.GetCombinedNamespaces( ( 'creator', 'series', 'title', 'volume', 'chapter', 'page' ) ), result )
        
    
    def test_delete_pending( self ):
        
        self.assertEqual( self._other_tags_manager.GetPending( self._pending_service_key ), { 'pending' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._pending_service_key ), { 'petitioned' } )
        
        self._other_tags_manager.DeletePending( self._pending_service_key )
        
        self.assertEqual( self._other_tags_manager.GetPending( self._pending_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._pending_service_key ), set() )
        
    
    def test_get_current( self ):
        
        self.assertEqual( self._tags_manager.GetCurrent( self._first_key ), { 'current', u'\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1' } )
        self.assertEqual( self._tags_manager.GetCurrent( self._second_key ), { 'deleted', u'\u2835' } )
        self.assertEqual( self._tags_manager.GetCurrent( self._third_key ), { 'petitioned' } )
        
        self.assertEqual( self._tags_manager.GetCurrent(), { 'current', 'deleted', u'\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1', 'petitioned' } )
        
    
    def test_get_deleted( self ):
        
        self.assertEqual( self._tags_manager.GetDeleted( self._first_key ), { 'deleted' } )
        self.assertEqual( self._tags_manager.GetDeleted( self._second_key ), { 'current' } )
        self.assertEqual( self._tags_manager.GetDeleted( self._third_key ), { 'pending' } )
        
        self.assertEqual( self._tags_manager.GetDeleted(), { 'deleted', 'current', 'pending' } )
        
    
    def test_get_namespace_slice( self ):
        
        self.assertEqual( self._tags_manager.GetNamespaceSlice( ( 'creator', 'series' ) ), frozenset( { 'creator:tsutomu nihei', 'series:blame!' } ) )
        self.assertEqual( self._tags_manager.GetNamespaceSlice( () ), frozenset() )
        
    
    def test_get_num_tags( self ):
        
        self.assertEqual( self._tags_manager.GetNumTags( self._first_key, include_current_tags = False, include_pending_tags = False ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._first_key, include_current_tags = True, include_pending_tags = False ), 8 )
        self.assertEqual( self._tags_manager.GetNumTags( self._first_key, include_current_tags = False, include_pending_tags = True ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._first_key, include_current_tags = True, include_pending_tags = True ), 8 )
        
        self.assertEqual( self._tags_manager.GetNumTags( self._second_key, include_current_tags = False, include_pending_tags = False ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._second_key, include_current_tags = True, include_pending_tags = False ), 2 )
        self.assertEqual( self._tags_manager.GetNumTags( self._second_key, include_current_tags = False, include_pending_tags = True ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( self._second_key, include_current_tags = True, include_pending_tags = True ), 3 )
        
        self.assertEqual( self._tags_manager.GetNumTags( self._third_key, include_current_tags = False, include_pending_tags = False ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._third_key, include_current_tags = True, include_pending_tags = False ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( self._third_key, include_current_tags = False, include_pending_tags = True ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._third_key, include_current_tags = True, include_pending_tags = True ), 1 )
        
        self.assertEqual( self._tags_manager.GetNumTags( CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = False, include_pending_tags = False ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = False ), 10 )
        self.assertEqual( self._tags_manager.GetNumTags( CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = False, include_pending_tags = True ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( CC.COMBINED_TAG_SERVICE_KEY, include_current_tags = True, include_pending_tags = True ), 11 )
        
    
    def test_get_pending( self ):
        
        self.assertEqual( self._tags_manager.GetPending( self._first_key ), set() )
        self.assertEqual( self._tags_manager.GetPending( self._second_key ), { 'pending' } )
        self.assertEqual( self._tags_manager.GetPending( self._third_key ), set() )
        
        self.assertEqual( self._tags_manager.GetPending(), { 'pending' } )
        
    
    def test_get_petitioned( self ):
        
        self.assertEqual( self._tags_manager.GetPetitioned( self._first_key ), set() )
        self.assertEqual( self._tags_manager.GetPetitioned( self._second_key ), { 'petitioned' } )
        self.assertEqual( self._tags_manager.GetPetitioned( self._third_key ), set() )
        
        self.assertEqual( self._tags_manager.GetPetitioned(), { 'petitioned' } )
        
    
    def test_get_service_keys_to_statuses_to_tags( self ):
        
        s = self._tags_manager.GetServiceKeysToStatusesToTags()
        
        self.assertEqual( s[ self._first_key ], self._service_keys_to_statuses_to_tags[ self._first_key ] )
        self.assertEqual( s[ self._second_key ], self._service_keys_to_statuses_to_tags[ self._second_key ] )
        self.assertEqual( s[ self._third_key ], self._service_keys_to_statuses_to_tags[ self._third_key ] )
        
    
    def test_get_statuses_to_tags( self ):
        
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._first_key ), self._service_keys_to_statuses_to_tags[ self._first_key ] )
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._second_key ), self._service_keys_to_statuses_to_tags[ self._second_key ] )
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._third_key ), self._service_keys_to_statuses_to_tags[ self._third_key ] )
        
    
    def test_has_tag( self ):
        
        self.assertTrue( self._tags_manager.HasTag( u'\u2835' ) )
        self.assertFalse( self._tags_manager.HasTag( 'not_exist' ) )
        
    
    def test_process_content_update( self ):
        
        hashes = { HydrusData.GenerateKey() for i in range( 6 ) }
        
        #
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), set() )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'hello', hashes, 'reason' ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), { 'hello' } )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), set() )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'hello', hashes, 'reason' ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), { 'hello' } )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_key, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_key ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_key ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
    
    def test_reset_service( self ):
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._reset_service_key ), { 'reset_current' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._reset_service_key ), { 'reset_deleted' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._reset_service_key ), { 'reset_pending' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._reset_service_key ), { 'reset_petitioned' } )
        
        self._other_tags_manager.ResetService( self._reset_service_key )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._reset_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._reset_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._reset_service_key ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._reset_service_key ), set() )
        
    
class TestTagObjects( unittest.TestCase ):
    
    def test_predicates( self ):
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'tag' )
        
        self.assertEqual( p.GetUnicode(), u'tag' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'tag', min_current_count = 1, min_pending_count = 2 )
        
        self.assertEqual( p.GetUnicode( with_count = False ), u'tag' )
        self.assertEqual( p.GetUnicode( with_count = True ), u'tag (1) (+2)' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'tag', False )
        
        self.assertEqual( p.GetUnicode(), u'-tag' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'tag', False, 1, 2 )
        
        self.assertEqual( p.GetUnicode( with_count = False ), u'-tag' )
        self.assertEqual( p.GetUnicode( with_count = True ), u'-tag (1) (+2)' )
        
        #
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 1, 2, 3, 4 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:age < 1y2m3d4h' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_AGE, ( u'\u2248', 1, 2, 3, 4 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:age ' + u'\u2248' + ' 1y2m3d4h' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 1, 2, 3, 4 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:age > 1y2m3d4h' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_ARCHIVE, min_current_count = 1000 )
        
        self.assertEqual( p.GetUnicode(), u'system:archive (1,000)' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_DURATION, ( '<', 200 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:duration < 200 milliseconds' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_EVERYTHING, min_current_count = 2000 )
        
        self.assertEqual( p.GetUnicode(), u'system:everything (2,000)' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( True, HC.CONTENT_STATUS_CURRENT, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.GetUnicode(), u'system:is currently in local files' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_FILE_SERVICE, ( False, HC.CONTENT_STATUS_PENDING, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.GetUnicode(), u'system:is not pending to local files' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_HASH, ( 'abcd'.decode( 'hex' ), 'sha256' ) )
        
        self.assertEqual( p.GetUnicode(), u'system:sha256 hash is abcd' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_HEIGHT, ( '<', 2000 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:height < 2,000' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_INBOX, min_current_count = 1000 )
        
        self.assertEqual( p.GetUnicode(), u'system:inbox (1,000)' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_LIMIT, 2000 )
        
        self.assertEqual( p.GetUnicode(), u'system:limit is 2,000' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_LOCAL, min_current_count = 100 )
        
        self.assertEqual( p.GetUnicode(), u'system:local (100)' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_MIME, set( HC.IMAGES ).intersection( HC.SEARCHABLE_MIMES ) )
        
        self.assertEqual( p.GetUnicode(), u'system:mime is image' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_MIME, ( HC.VIDEO_WEBM, ) )
        
        self.assertEqual( p.GetUnicode(), u'system:mime is video/webm' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_MIME, ( HC.VIDEO_WEBM, HC.IMAGE_GIF ) )
        
        self.assertEqual( p.GetUnicode(), u'system:mime is video/webm, image/gif' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_NOT_LOCAL, min_current_count = 100 )
        
        self.assertEqual( p.GetUnicode(), u'system:not local (100)' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '<', 2 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:number of tags < 2' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_NUM_WORDS, ( '<', 5000 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:number of words < 5,000' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_RATING, ( '>', 0.2, CC.LOCAL_FILE_SERVICE_KEY ) )
        
        self.assertEqual( p.GetUnicode(), u'system:rating for local files > 0.2' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 16, 9 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:ratio = 16:9' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_SIMILAR_TO, ( 'abcd'.decode( 'hex' ), 5 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:similar to abcd using max hamming of 5' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '>', 5, 1048576 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:size > 5MB' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_UNTAGGED, HC.IMAGES )
        
        self.assertEqual( p.GetUnicode(), u'system:untagged' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_WIDTH, ( '=', 1920 ) )
        
        self.assertEqual( p.GetUnicode(), u'system:width = 1,920' )
        
        #
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_NAMESPACE, 'series' )
        
        self.assertEqual( p.GetUnicode(), u'series:*anything*' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'series', False )
        
        self.assertEqual( p.GetUnicode(), u'-series' )
        
        #
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_WILDCARD, 'a*i:o*' )
        
        self.assertEqual( p.GetUnicode(), u'a*i:o*' )
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'a*i:o*', False )
        
        self.assertEqual( p.GetUnicode(), u'-a*i:o*' )
        
        #
        
        p = ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'series:game of thrones' )
        
        self.assertEqual( p.GetUnicode(), u'    series:game of thrones' )
        
    
class TestTagParents( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._first_key = HydrusData.GenerateKey()
        self._second_key = HydrusData.GenerateKey()
        self._third_key = HydrusData.GenerateKey()
        
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
        
        tag_parents[ self._first_key ] = first_dict
        tag_parents[ self._second_key ] = second_dict
        tag_parents[ self._third_key ] = third_dict
        
        HydrusGlobals.test_controller.SetRead( 'tag_parents', tag_parents )
        
        self._tag_parents_manager = ClientCaches.TagParentsManager( HydrusGlobals.client_controller )
        
    
    def test_expand_predicates( self ):
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'grandmother', min_current_count = 10 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'grandfather', min_current_count = 15 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'not_exist', min_current_count = 20 ) )
        
        self.assertEqual( self._tag_parents_manager.ExpandPredicates( CC.COMBINED_TAG_SERVICE_KEY, predicates ), predicates )
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'child', min_current_count = 10 ) )
        
        results = []
        
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'child', min_current_count = 10 ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'mother' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'father' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandmother' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandfather' ) )
        
        self.assertEqual( set( self._tag_parents_manager.ExpandPredicates( CC.COMBINED_TAG_SERVICE_KEY, predicates ) ), set( results ) )
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_NAMESPACE, 'series' ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'child', min_current_count = 10 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'cousin', min_current_count = 5 ) )
        
        results = []
        
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_NAMESPACE, 'series' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'child', min_current_count = 10 ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'mother' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'father' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandmother' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandfather' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'cousin', min_current_count = 5 ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'aunt' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'uncle' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandmother' ) )
        results.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandfather' ) )
        
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
    def setUpClass( self ):
        
        self._first_key = HydrusData.GenerateKey()
        self._second_key = HydrusData.GenerateKey()
        
        tag_siblings = collections.defaultdict( HydrusData.default_dict_set )
        
        first_dict = HydrusData.default_dict_set()
        
        first_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'ishygddt', 'i sure hope you guys don\'t do that' ), ( 'character:rei ayanami', 'character:ayanami rei' ), ( 'tree_1', 'tree_3' ), ( 'tree_2', 'tree_3' ), ( 'tree_3', 'tree_5' ), ( 'tree_4', 'tree_5' ), ( 'tree_5', 'tree_6' ), ( 'current_a', 'current_b' ), ( 'chain_a', 'chain_b' ), ( 'chain_b', 'chain_c' ), ( 'closed_loop', 'closed_loop' ), ( 'loop_a', 'loop_b' ), ( 'loop_b', 'loop_c' ), ( 'loop_c', 'loop_a' ) }
        first_dict[ HC.CONTENT_STATUS_DELETED ] = { ( 'deleted_a', 'deleted_b' ) }
        
        second_dict = HydrusData.default_dict_set()
        
        second_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'loop_c', 'loop_a' ), ( 'current_a', 'current_b' ), ( 'petitioned_a', 'petitioned_b' ) }
        second_dict[ HC.CONTENT_STATUS_DELETED ] = { ( 'pending_a', 'pending_b' ) }
        second_dict[ HC.CONTENT_STATUS_PENDING ] = { ( 'pending_a', 'pending_b' ) }
        second_dict[ HC.CONTENT_STATUS_PETITIONED ] = { ( 'petitioned_a', 'petitioned_b' ) }
        
        tag_siblings[ self._first_key ] = first_dict
        tag_siblings[ self._second_key ] = second_dict
        
        HydrusGlobals.test_controller.SetRead( 'tag_siblings', tag_siblings )
        
        self._tag_siblings_manager = ClientCaches.TagSiblingsManager( HydrusGlobals.client_controller )
        
    
    def test_autocomplete( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'ishy*' ) ), set( [ 'ishygddt', 'i sure hope you guys don\'t do that' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'i su*' ) ), set( [ 'ishygddt', 'i sure hope you guys don\'t do that' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'ayan*' ) ), set( [ 'character:rei ayanami', 'character:ayanami rei' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'rei*' ) ), set( [ 'character:rei ayanami', 'character:ayanami rei' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'character:ayan*' ) ), set( [ 'character:rei ayanami', 'character:ayanami rei' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'character:rei*' ) ), set( [ 'character:rei ayanami', 'character:ayanami rei' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._second_key, 'ishy*' ) ), set() )
        
    
    def test_collapse_predicates( self ):
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'chain_a', min_current_count = 10 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'chain_b', min_current_count = 5 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'chain_c', min_current_count = 20 ) )
        
        results = [ ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'chain_c', min_current_count = 20, max_current_count = 35 ) ]
        
        self.assertEqual( self._tag_siblings_manager.CollapsePredicates( self._first_key, predicates ), results )
        
        predicates = []
        
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'chain_a', min_current_count = 10 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'chain_b', min_current_count = 5 ) )
        predicates.append( ClientSearch.Predicate( HC.PREDICATE_TYPE_TAG, 'chain_c', min_current_count = 20 ) )
        
        ( result, ) = self._tag_siblings_manager.CollapsePredicates( self._first_key, predicates )
        
        self.assertEqual( result.GetCount(), 20 )
        self.assertEqual( result.GetUnicode(), u'chain_c (20-35)' )
        
    
    def test_chain( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'chai*' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'chain_a' ), 'chain_c' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'chain_b' ), 'chain_c' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'chain_c' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'chain_a' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'chain_b' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'chain_c' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'chain_a', 'chain_b' ] ) ), set( [ 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'chain_a', 'chain_b', 'chain_c' ] ) ), set( [ 'chain_c' ] ) )
        
    
    def test_current( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._second_key, 'curr*' ) ), set( [ 'current_a', 'current_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'current_a' ), 'current_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'current_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'current_a' ) ), set( [ 'current_a', 'current_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'current_b' ) ), set( [ 'current_a', 'current_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'chain_a', 'chain_b' ] ) ), set( [ 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'chain_a', 'chain_b', 'chain_c' ] ) ), set( [ 'chain_c' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'chain_a' : 10, 'chain_b' : 5 } ), { 'chain_c' : 15 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'chain_a' : 10, 'chain_b' : 5, 'chain_c' : 20 } ), { 'chain_c' : 35 } )
        
    
    def test_deleted( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'dele*' ) ), set() )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'deleted_a' ), None )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'deleted_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'deleted_a' ) ), set( [ 'deleted_a' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'deleted_b' ) ), set( [ 'deleted_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'deleted_a', 'deleted_b' ] ) ), set( [ 'deleted_a', 'deleted_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'deleted_a' : 10, 'deleted_b' : 5 } ), { 'deleted_a' : 10, 'deleted_b' : 5 } )
        
    
    def test_no_loop( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'loop*' ) ), set( [ 'loop_a', 'loop_b', 'loop_c' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._first_key, 'closed_loop' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._first_key, 'closed_loop' ) ), set( [ 'closed_loop' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._first_key, [ 'closed_loop' ] ) ), set( [ 'closed_loop' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._first_key, { 'closed_loop' : 10 } ), { 'closed_loop' : 10 } )
        
    
    def test_not_exist( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._second_key, 'not_*' ) ), set() )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'not_exist' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'not_exist' ) ), set( [ 'not_exist' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'not_exist' ] ) ), set( [ 'not_exist' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'not_exist' : 10 } ), { 'not_exist' : 10 } )
        
    
    def test_pending_overwrite( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._second_key, 'pend*' ) ), set( [ 'pending_a', 'pending_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'pending_a' ), 'pending_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'pending_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'pending_a' ) ), set( [ 'pending_a', 'pending_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'pending_b' ) ), set( [ 'pending_a', 'pending_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'pending_a' ] ) ), set( [ 'pending_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'pending_a', 'pending_b' ] ) ), set( [ 'pending_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'pending_a' : 10 } ), { 'pending_b' : 10 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'pending_a' : 10, 'pending_b' : 5 } ), { 'pending_b' : 15 } )
        
    
    def test_petitioned_no_overwrite( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._second_key, 'petitioned_a*' ) ), set( [ 'petitioned_a', 'petitioned_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'petitioned_a' ), 'petitioned_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( self._second_key, 'petitioned_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'petitioned_a' ) ), set( [ 'petitioned_a', 'petitioned_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( self._second_key, 'petitioned_b' ) ), set( [ 'petitioned_a', 'petitioned_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'petitioned_a' ] ) ), set( [ 'petitioned_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( self._second_key, [ 'petitioned_a', 'petitioned_b' ] ) ), set( [ 'petitioned_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'petitioned_a' : 10 } ), { 'petitioned_b' : 10 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( self._second_key, { 'petitioned_a' : 10, 'petitioned_b' : 5 } ), { 'petitioned_b' : 15 } )
        
    
    def test_tree( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( self._first_key, 'tree*' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        
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
        
    
