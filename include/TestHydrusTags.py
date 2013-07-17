import collections
import HydrusConstants as HC
import HydrusTags
import os
import TestConstants
import unittest

class TestMergeTagsManagers( unittest.TestCase ):
    
    def test_merge( self ):
        
        first = TestConstants.GenerateClientServiceIdentifier( HC.LOCAL_TAG )
        second = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        third = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        
        tag_service_precedence = [ first, second, third ]
        
        #
        
        service_identifiers_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
        
        service_identifiers_to_statuses_to_tags[ first ][ HC.CURRENT ] = { 'current_1', 'series:blame!' }
        
        service_identifiers_to_statuses_to_tags[ second ][ HC.CURRENT ] = { 'current_duplicate_1', 'character:cibo' }
        service_identifiers_to_statuses_to_tags[ second ][ HC.DELETED ] = { 'current_1' }
        service_identifiers_to_statuses_to_tags[ second ][ HC.PENDING ] = { 'pending_1', 'creator:tsutomu nihei' }
        service_identifiers_to_statuses_to_tags[ second ][ HC.PETITIONED ] = { 'petitioned_1' }
        
        service_identifiers_to_statuses_to_tags[ third ][ HC.CURRENT ] = { 'current_duplicate', 'current_duplicate_1' }
        service_identifiers_to_statuses_to_tags[ third ][ HC.PENDING ] = { 'volume:3' }
        
        tags_manager_1 = HydrusTags.TagsManager( tag_service_precedence, service_identifiers_to_statuses_to_tags )
        
        tags_manager_1._RecalcCombined()
        
        #
        
        service_identifiers_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
        
        service_identifiers_to_statuses_to_tags[ first ][ HC.CURRENT ] = { 'current_2', 'series:blame!', 'chapter:1' }
        service_identifiers_to_statuses_to_tags[ first ][ HC.DELETED ] = { 'deleted_2' }
        
        service_identifiers_to_statuses_to_tags[ second ][ HC.CURRENT ] = { 'current_duplicate'  }
        service_identifiers_to_statuses_to_tags[ second ][ HC.PENDING ] = { 'architecture', 'chapter:2' }
        
        service_identifiers_to_statuses_to_tags[ third ][ HC.CURRENT ] = { 'current_duplicate' }
        
        tags_manager_2 = HydrusTags.TagsManager( tag_service_precedence, service_identifiers_to_statuses_to_tags )
        
        tags_manager_2._RecalcCombined()
        
        #
        
        service_identifiers_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
        
        service_identifiers_to_statuses_to_tags[ second ][ HC.CURRENT ] = { 'page:4', 'page:5' }
        service_identifiers_to_statuses_to_tags[ second ][ HC.PENDING ] = { 'title:double page spread' }
        
        tags_manager_3 = HydrusTags.TagsManager( tag_service_precedence, service_identifiers_to_statuses_to_tags )
        
        tags_manager_3._RecalcCombined()
        
        #
        
        tags_managers = ( tags_manager_1, tags_manager_2, tags_manager_3 )
        
        tags_manager = HydrusTags.MergeTagsManagers( tag_service_precedence, tags_managers )
        
        #
        
        self.assertEqual( tags_manager.GetCSTVCP(), ( { 'tsutomu nihei' }, { 'blame!' }, { 'double page spread' }, { 3 }, { 1, 2 }, { 4, 5 } ) )
        
        self.assertEqual( tags_manager.GetNamespaceSlice( ( 'character', ) ), frozenset( { 'character:cibo' } ) )
        
    
class TestTagsManager( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._first = TestConstants.GenerateClientServiceIdentifier( HC.LOCAL_TAG )
        self._second = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        self._third = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        
        tag_service_precedence = [ self._first, self._second, self._third ]
        
        service_identifiers_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
        
        service_identifiers_to_statuses_to_tags[ self._first ][ HC.CURRENT ] = { 'current', u'\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1' }
        service_identifiers_to_statuses_to_tags[ self._first ][ HC.DELETED ] = { 'deleted' }
        
        service_identifiers_to_statuses_to_tags[ self._second ][ HC.CURRENT ] = { 'deleted', u'\u2835' }
        service_identifiers_to_statuses_to_tags[ self._second ][ HC.DELETED ] = { 'current' }
        service_identifiers_to_statuses_to_tags[ self._second ][ HC.PENDING ] = { 'pending' }
        service_identifiers_to_statuses_to_tags[ self._second ][ HC.PETITIONED ] = { 'petitioned' }
        
        service_identifiers_to_statuses_to_tags[ self._third ][ HC.CURRENT ] = { 'petitioned' }
        service_identifiers_to_statuses_to_tags[ self._third ][ HC.DELETED ] = { 'pending' }
        
        self._tags_manager = HydrusTags.TagsManager( tag_service_precedence, service_identifiers_to_statuses_to_tags )
        
        self._tags_manager._RecalcCombined()
        
        self._service_identifiers_to_statuses_to_tags = service_identifiers_to_statuses_to_tags
        
        #
        
        self._pending_service_identifier = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        self._content_update_service_identifier = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        self._reset_service_identifier = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        
        tag_service_precedence = [ self._pending_service_identifier, self._content_update_service_identifier, self._reset_service_identifier ]
        
        other_service_identifiers_to_statuses_to_tags = collections.defaultdict( HC.default_dict_set )
        
        other_service_identifiers_to_statuses_to_tags[ self._pending_service_identifier ][ HC.PENDING ] = { 'pending' }
        other_service_identifiers_to_statuses_to_tags[ self._pending_service_identifier ][ HC.PETITIONED ] = { 'petitioned' }
        
        other_service_identifiers_to_statuses_to_tags[ self._reset_service_identifier ][ HC.CURRENT ] = { 'reset_current' }
        other_service_identifiers_to_statuses_to_tags[ self._reset_service_identifier ][ HC.DELETED ] = { 'reset_deleted' }
        other_service_identifiers_to_statuses_to_tags[ self._reset_service_identifier ][ HC.PENDING ] = { 'reset_pending' }
        other_service_identifiers_to_statuses_to_tags[ self._reset_service_identifier ][ HC.PETITIONED ] = { 'reset_petitioned' }
        
        self._other_tags_manager = HydrusTags.TagsManager( tag_service_precedence, other_service_identifiers_to_statuses_to_tags )
        
        self._other_tags_manager._RecalcCombined()
        
        self._other_service_identifiers_to_statuses_to_tags = other_service_identifiers_to_statuses_to_tags
        
    
    def test_get_cstvcp( self ):
        
        self.assertEqual( self._tags_manager.GetCSTVCP(), ( { 'tsutomu nihei' }, { 'blame!' }, { 'test title' }, { 3 }, { 2 }, { 1 } ) )
        
    
    def test_delete_pending( self ):
        
        self.assertEqual( self._other_tags_manager.GetPending( self._pending_service_identifier ), { 'pending' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._pending_service_identifier ), { 'petitioned' } )
        
        self._other_tags_manager.DeletePending( self._pending_service_identifier )
        
        self.assertEqual( self._other_tags_manager.GetPending( self._pending_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._pending_service_identifier ), set() )
        
    
    def test_get_current( self ):
        
        self.assertEqual( self._tags_manager.GetCurrent( self._first ), { 'current', u'\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1' } )
        self.assertEqual( self._tags_manager.GetCurrent( self._second ), { 'deleted', u'\u2835' } )
        self.assertEqual( self._tags_manager.GetCurrent( self._third ), { 'petitioned' } )
        
        self.assertEqual( self._tags_manager.GetCurrent(), { 'current', u'\u2835', 'creator:tsutomu nihei', 'series:blame!', 'title:test title', 'volume:3', 'chapter:2', 'page:1', 'petitioned' } )
        
    
    def test_get_deleted( self ):
        
        self.assertEqual( self._tags_manager.GetDeleted( self._first ), { 'deleted' } )
        self.assertEqual( self._tags_manager.GetDeleted( self._second ), { 'current' } )
        self.assertEqual( self._tags_manager.GetDeleted( self._third ), { 'pending' } )
        
        self.assertEqual( self._tags_manager.GetDeleted(), set() ) # combined tag service does not track deleted
        
    
    def test_get_namespace_slice( self ):
        
        self.assertEqual( self._tags_manager.GetNamespaceSlice( ( 'creator', 'series' ), collapse = False ), frozenset( { 'creator:tsutomu nihei', 'series:blame!' } ) )
        self.assertEqual( self._tags_manager.GetNamespaceSlice( (), collapse = False ), frozenset() )
        
        self.assertEqual( self._tags_manager.GetNamespaceSlice( ( 'creator', 'series' ) ), frozenset( { 'creator:tsutomu nihei', 'series:blame!' } ) )
        self.assertEqual( self._tags_manager.GetNamespaceSlice( () ), frozenset() )
        
    
    def test_get_num_tags( self ):
        
        self.assertEqual( self._tags_manager.GetNumTags( self._first, include_current_tags = False, include_pending_tags = False ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._first, include_current_tags = True, include_pending_tags = False ), 8 )
        self.assertEqual( self._tags_manager.GetNumTags( self._first, include_current_tags = False, include_pending_tags = True ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._first, include_current_tags = True, include_pending_tags = True ), 8 )
        
        self.assertEqual( self._tags_manager.GetNumTags( self._second, include_current_tags = False, include_pending_tags = False ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._second, include_current_tags = True, include_pending_tags = False ), 2 )
        self.assertEqual( self._tags_manager.GetNumTags( self._second, include_current_tags = False, include_pending_tags = True ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( self._second, include_current_tags = True, include_pending_tags = True ), 3 )
        
        self.assertEqual( self._tags_manager.GetNumTags( self._third, include_current_tags = False, include_pending_tags = False ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._third, include_current_tags = True, include_pending_tags = False ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( self._third, include_current_tags = False, include_pending_tags = True ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( self._third, include_current_tags = True, include_pending_tags = True ), 1 )
        
        self.assertEqual( self._tags_manager.GetNumTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, include_current_tags = False, include_pending_tags = False ), 0 )
        self.assertEqual( self._tags_manager.GetNumTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, include_current_tags = True, include_pending_tags = False ), 9 )
        self.assertEqual( self._tags_manager.GetNumTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, include_current_tags = False, include_pending_tags = True ), 1 )
        self.assertEqual( self._tags_manager.GetNumTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, include_current_tags = True, include_pending_tags = True ), 10 )
        
    
    def test_get_pending( self ):
        
        self.assertEqual( self._tags_manager.GetPending( self._first ), set() )
        self.assertEqual( self._tags_manager.GetPending( self._second ), { 'pending' } )
        self.assertEqual( self._tags_manager.GetPending( self._third ), set() )
        
        self.assertEqual( self._tags_manager.GetPending(), { 'pending' } )
        
    
    def test_get_petitioned( self ):
        
        self.assertEqual( self._tags_manager.GetPetitioned( self._first ), set() )
        self.assertEqual( self._tags_manager.GetPetitioned( self._second ), { 'petitioned' } )
        self.assertEqual( self._tags_manager.GetPetitioned( self._third ), set() )
        
        self.assertEqual( self._tags_manager.GetPetitioned(), set() ) # combined tag service does not track petitioned
        
    
    def test_get_service_identifiers_to_statuses_to_tags( self ):
        
        self.assertEqual( self._tags_manager.GetServiceIdentifiersToStatusesToTags(), self._service_identifiers_to_statuses_to_tags )
        
    
    def test_get_statuses_to_tags( self ):
        
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._first ), self._service_identifiers_to_statuses_to_tags[ self._first ] )
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._second ), self._service_identifiers_to_statuses_to_tags[ self._second ] )
        self.assertEqual( self._tags_manager.GetStatusesToTags( self._third ), self._service_identifiers_to_statuses_to_tags[ self._third ] )
        
    
    def test_has_tag( self ):
        
        self.assertTrue( self._tags_manager.HasTag( u'\u2835' ) )
        self.assertFalse( self._tags_manager.HasTag( 'not_exist' ) )
        
    
    def test_process_content_update( self ):
        
        hashes = { os.urandom( 32 ) for i in range( 6 ) }
        
        #
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PENDING, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PENDING, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), set() )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'hello', hashes, 'reason' ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), { 'hello' } )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_RESCIND_PETITION, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), set() )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'hello', hashes, 'reason' ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), { 'hello' } )
        
        self.assertIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
        #
        
        content_update = HC.ContentUpdate( HC.CONTENT_DATA_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'hello', hashes ) )
        
        self._other_tags_manager.ProcessContentUpdate( self._content_update_service_identifier, content_update )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._content_update_service_identifier ), { 'hello' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._content_update_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._content_update_service_identifier ), set() )
        
        self.assertNotIn( 'hello', self._other_tags_manager.GetCurrent() )
        self.assertNotIn( 'hello', self._other_tags_manager.GetPending() )
        
    
    def test_reset_service( self ):
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._reset_service_identifier ), { 'reset_current' } )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._reset_service_identifier ), { 'reset_deleted' } )
        self.assertEqual( self._other_tags_manager.GetPending( self._reset_service_identifier ), { 'reset_pending' } )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._reset_service_identifier ), { 'reset_petitioned' } )
        
        self._other_tags_manager.ResetService( self._reset_service_identifier )
        
        self.assertEqual( self._other_tags_manager.GetCurrent( self._reset_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetDeleted( self._reset_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPending( self._reset_service_identifier ), set() )
        self.assertEqual( self._other_tags_manager.GetPetitioned( self._reset_service_identifier ), set() )
        
    
class TestTagParents( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._first = TestConstants.GenerateClientServiceIdentifier( HC.LOCAL_TAG )
        self._second = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        self._third = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        
        tag_service_precedence = [ self._first, self._second, self._third ]
        
        tag_parents = collections.defaultdict( HC.default_dict_set )
        
        first_dict = HC.default_dict_set()
        
        first_dict[ HC.CURRENT ] = { ( 'current_a', 'current_b' ), ( 'child', 'mother' ), ( 'child', 'father' ), ( 'sister', 'mother' ), ( 'sister', 'father' ), ( 'brother', 'mother' ), ( 'brother', 'father' ), ( 'mother', 'grandmother' ), ( 'mother', 'grandfather' ), ( 'aunt', 'grandmother' ), ( 'aunt', 'grandfather' ), ( 'cousin', 'aunt' ), ( 'cousin', 'uncle' ), ( 'closed_loop', 'closed_loop' ), ( 'loop_a', 'loop_b' ), ( 'loop_b', 'loop_c' ) }
        first_dict[ HC.DELETED ] = { ( 'deleted_a', 'deleted_b' ) }
        
        second_dict = HC.default_dict_set()
        
        second_dict[ HC.CURRENT ] = { ( 'loop_c', 'loop_a' ), ( 'deleted_a', 'deleted_b' ) }
        second_dict[ HC.DELETED ] = { ( 'current_a', 'current_b' ) }
        second_dict[ HC.PENDING ] = { ( 'pending_a', 'pending_b' ) }
        second_dict[ HC.PETITIONED ] = { ( 'petitioned_a', 'petitioned_b' ) }
        
        third_dict = HC.default_dict_set()
        
        third_dict[ HC.CURRENT ] = { ( 'petitioned_a', 'petitioned_b' ) }
        third_dict[ HC.DELETED ] = { ( 'pending_a', 'pending_b' ) }
        
        tag_parents[ self._first ] = first_dict
        tag_parents[ self._second ] = second_dict
        tag_parents[ self._third ] = third_dict
        
        HC.app.SetRead( 'tag_service_precedence', tag_service_precedence )
        HC.app.SetRead( 'tag_parents', tag_parents )
        
        self._tag_parents_manager = HydrusTags.TagParentsManager()
        
    
    def test_expand_predicates( self ):
        
        predicates = []
        
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'grandmother' ), 10 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'grandfather' ), 15 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'not_exist' ), 20 ) )
        
        self.assertEqual( self._tag_parents_manager.ExpandPredicates( HC.COMBINED_TAG_SERVICE_IDENTIFIER, predicates ), predicates )
        
        predicates = []
        
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'child' ), 10 ) )
        
        results = []
        
        results.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'child' ), 10 ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'mother', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'father', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandmother', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandfather', None ) )
        
        self.assertEqual( set( self._tag_parents_manager.ExpandPredicates( HC.COMBINED_TAG_SERVICE_IDENTIFIER, predicates ) ), set( results ) )
        
        predicates = []
        
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'child' ), 10 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'cousin' ), 5 ) )
        
        results = []
        
        results.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'child' ), 10 ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'mother', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'father', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandmother', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandfather', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'cousin' ), 5 ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'aunt', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'uncle', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandmother', None ) )
        results.append( HC.Predicate( HC.PREDICATE_TYPE_PARENT, 'grandfather', None ) )
        
        self.assertEqual( set( self._tag_parents_manager.ExpandPredicates( HC.COMBINED_TAG_SERVICE_IDENTIFIER, predicates ) ), set( results ) )
        
    
    def test_expand_tags( self ):
        
        tags = { 'grandmother', 'grandfather' }
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, tags ), tags )
        
        tags = { 'child', 'cousin' }
        
        results = { 'child', 'mother', 'father', 'grandmother', 'grandfather', 'cousin', 'aunt', 'uncle', 'grandmother', 'grandfather' }
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, tags ), results )
        
    
    def test_grandparents( self ):
        
        self.assertEqual( set( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'child' ) ), { 'mother', 'father', 'grandmother', 'grandfather' } )
        self.assertEqual( set( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'mother' ) ), { 'grandmother', 'grandfather' } )
        self.assertEqual( set( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'grandmother' ) ), set() )
        
    
    def test_current_overwrite( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'current_a' ), [ 'current_b' ] )
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'current_b' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'current_a' ] ), { 'current_a', 'current_b' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'current_b' ] ), { 'current_b' } )
        
    
    def test_deleted_overwrite( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'deleted_a' ), [] )
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'deleted_b' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'deleted_a' ] ), { 'deleted_a' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'deleted_b' ] ), { 'deleted_b' } )
        
    
    def test_no_loop( self ):
        
        self.assertEqual( set( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'loop_a' ) ), { 'loop_b', 'loop_c' } )
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'loop_b' ), [ 'loop_c' ] )
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'loop_c' ), [] )
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'closed_loop' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'loop_a' ] ), { 'loop_a', 'loop_b', 'loop_c' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'loop_b' ] ), { 'loop_b', 'loop_c' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'loop_c' ] ), { 'loop_c' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'closed_loop' ] ), { 'closed_loop' } )
        
    
    def test_not_exist( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'not_exist' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'not_exist' ] ), { 'not_exist' } )
        
    
    def test_pending_overwrite( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'pending_a' ), [ 'pending_b' ] )
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'pending_b' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'pending_a' ] ), { 'pending_a', 'pending_b' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'pending_b' ] ), { 'pending_b' } )
        
    
    def test_petitioned_no_overwrite( self ):
        
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'petitioned_a' ), [ 'petitioned_b' ] )
        self.assertEqual( self._tag_parents_manager.GetParents( HC.COMBINED_TAG_SERVICE_IDENTIFIER, 'petitioned_b' ), [] )
        
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'petitioned_a' ] ), { 'petitioned_a', 'petitioned_b' } )
        self.assertEqual( self._tag_parents_manager.ExpandTags( HC.COMBINED_TAG_SERVICE_IDENTIFIER, [ 'petitioned_b' ] ), { 'petitioned_b' } )
        
    
class TestTagSiblings( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._first = TestConstants.GenerateClientServiceIdentifier( HC.LOCAL_TAG )
        self._second = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        self._third = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        
        tag_service_precedence = [ self._first, self._second, self._third ]
        
        tag_siblings = collections.defaultdict( HC.default_dict_set )
        
        first_dict = HC.default_dict_set()
        
        first_dict[ HC.CURRENT ] = { ( 'ishygddt', 'i sure hope you guys don\'t do that' ), ( 'character:rei ayanami', 'character:ayanami rei' ), ( 'tree_1', 'tree_3' ), ( 'tree_2', 'tree_3' ), ( 'tree_3', 'tree_5' ), ( 'tree_4', 'tree_5' ), ( 'tree_5', 'tree_6' ), ( 'current_a', 'current_b' ), ( 'chain_a', 'chain_b' ), ( 'chain_b', 'chain_c' ), ( 'closed_loop', 'closed_loop' ), ( 'loop_a', 'loop_b' ), ( 'loop_b', 'loop_c' ) }
        first_dict[ HC.DELETED ] = { ( 'deleted_a', 'deleted_b' ) }
        
        second_dict = HC.default_dict_set()
        
        second_dict[ HC.CURRENT ] = { ( 'loop_c', 'loop_a' ), ( 'deleted_a', 'deleted_b' ) }
        second_dict[ HC.DELETED ] = { ( 'current_a', 'current_b' ) }
        second_dict[ HC.PENDING ] = { ( 'pending_a', 'pending_b' ) }
        second_dict[ HC.PETITIONED ] = { ( 'petitioned_a', 'petitioned_b' ) }
        
        third_dict = HC.default_dict_set()
        
        third_dict[ HC.CURRENT ] = { ( 'petitioned_a', 'petitioned_b' ) }
        third_dict[ HC.DELETED ] = { ( 'pending_a', 'pending_b' ) }
        
        tag_siblings[ self._first ] = first_dict
        tag_siblings[ self._second ] = second_dict
        tag_siblings[ self._third ] = third_dict
        
        HC.app.SetRead( 'tag_service_precedence', tag_service_precedence )
        HC.app.SetRead( 'tag_siblings', tag_siblings )
        
        self._tag_siblings_manager = HydrusTags.TagSiblingsManager()
        
    
    def test_autocomplete( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'ishy' ) ), set( [ 'ishygddt', 'i sure hope you guys don\'t do that' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'i su' ) ), set( [ 'ishygddt', 'i sure hope you guys don\'t do that' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'ayan' ) ), set( [ 'character:rei ayanami', 'character:ayanami rei' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'rei' ) ), set( [ 'character:rei ayanami', 'character:ayanami rei' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'character:ayan' ) ), set( [ 'character:rei ayanami', 'character:ayanami rei' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'character:rei' ) ), set( [ 'character:rei ayanami', 'character:ayanami rei' ] ) )
        
    
    def test_collapse_namespace( self ):
        
        self.assertEqual( self._tag_siblings_manager.CollapseNamespacedTags( 'character', [ 'ayanami rei', 'rei ayanami', 'ikari shinji' ] ), set( [ 'ayanami rei', 'ikari shinji' ] ) )
        
    
    def test_collapse_predicates( self ):
        
        predicates = []
        
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'chain_a' ), 10 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'chain_b' ), 5 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'chain_c' ), 20 ) )
        
        results = [ HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'chain_c' ), 35 ) ]
        
        self.assertEqual( self._tag_siblings_manager.CollapsePredicates( predicates ), results )
        
        predicates = []
        
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'chain_a' ), 10 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'chain_b' ), 5 ) )
        predicates.append( HC.Predicate( HC.PREDICATE_TYPE_TAG, ( '+', 'chain_c' ), 20 ) )
        
        ( result, ) = self._tag_siblings_manager.CollapsePredicates( predicates )
        
        self.assertEqual( result.GetCount(), 35 )
        
    
    def test_chain( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'chai' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'chain_a' ), 'chain_c' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'chain_b' ), 'chain_c' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'chain_c' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'chain_a' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'chain_b' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'chain_c' ) ), set( [ 'chain_a', 'chain_b', 'chain_c' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'chain_a', 'chain_b' ] ) ), set( [ 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'chain_a', 'chain_b', 'chain_c' ] ) ), set( [ 'chain_c' ] ) )
        
        # collapsetagstocount
        
    
    def test_current_overwrite( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'curr' ) ), set( [ 'current_a', 'current_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'current_a' ), 'current_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'current_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'current_a' ) ), set( [ 'current_a', 'current_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'current_b' ) ), set( [ 'current_a', 'current_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'chain_a', 'chain_b' ] ) ), set( [ 'chain_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'chain_a', 'chain_b', 'chain_c' ] ) ), set( [ 'chain_c' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'chain_a' : 10, 'chain_b' : 5 } ), { 'chain_c' : 15 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'chain_a' : 10, 'chain_b' : 5, 'chain_c' : 20 } ), { 'chain_c' : 35 } )
        
    
    def test_deleted_overwrite( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'dele' ) ), set() )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'deleted_a' ), None )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'deleted_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'deleted_a' ) ), set( [ 'deleted_a' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'deleted_b' ) ), set( [ 'deleted_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'deleted_a', 'deleted_b' ] ) ), set( [ 'deleted_a', 'deleted_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'deleted_a' : 10, 'deleted_b' : 5 } ), { 'deleted_a' : 10, 'deleted_b' : 5 } )
        
    
    def test_no_loop( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'loop' ) ), set( [ 'loop_a', 'loop_b', 'loop_c' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'loop_a' ), 'loop_c' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'loop_b' ), 'loop_c' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'loop_c' ), None )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'closed_loop' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'loop_a' ) ), set( [ 'loop_a', 'loop_b', 'loop_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'loop_b' ) ), set( [ 'loop_a', 'loop_b', 'loop_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'loop_c' ) ), set( [ 'loop_a', 'loop_b', 'loop_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'closed_loop' ) ), set( [ 'closed_loop' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'loop_a', 'loop_b' ] ) ), set( [ 'loop_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'loop_a', 'loop_b', 'loop_c' ] ) ), set( [ 'loop_c' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'loop_a', 'loop_b', 'loop_c', 'closed_loop' ] ) ), set( [ 'loop_c', 'closed_loop' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'loop_a' : 10, 'loop_b' : 5 } ), { 'loop_c' : 15 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'loop_a' : 10, 'loop_b' : 5, 'loop_c' : 20 } ), { 'loop_c' : 35 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'closed_loop' : 10 } ), { 'closed_loop' : 10 } )
        
    
    def test_not_exist( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'not_' ) ), set() )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'not_exist' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'not_exist' ) ), set( [ 'not_exist' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'not_exist' ] ) ), set( [ 'not_exist' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'not_exist' : 10 } ), { 'not_exist' : 10 } )
        
    
    def test_pending_overwrite( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'pend' ) ), set( [ 'pending_a', 'pending_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'pending_a' ), 'pending_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'pending_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'pending_a' ) ), set( [ 'pending_a', 'pending_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'pending_b' ) ), set( [ 'pending_a', 'pending_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'pending_a' ] ) ), set( [ 'pending_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'pending_a', 'pending_b' ] ) ), set( [ 'pending_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'pending_a' : 10 } ), { 'pending_b' : 10 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'pending_a' : 10, 'pending_b' : 5 } ), { 'pending_b' : 15 } )
        
    
    def test_petitioned_no_overwrite( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'petitioned_a' ) ), set( [ 'petitioned_a', 'petitioned_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'petitioned_a' ), 'petitioned_b' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'petitioned_b' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'petitioned_a' ) ), set( [ 'petitioned_a', 'petitioned_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'petitioned_b' ) ), set( [ 'petitioned_a', 'petitioned_b' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'petitioned_a' ] ) ), set( [ 'petitioned_b' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'petitioned_a', 'petitioned_b' ] ) ), set( [ 'petitioned_b' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'petitioned_a' : 10 } ), { 'petitioned_b' : 10 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'petitioned_a' : 10, 'petitioned_b' : 5 } ), { 'petitioned_b' : 15 } )
        
    
    def test_tree( self ):
        
        self.assertEqual( set( self._tag_siblings_manager.GetAutocompleteSiblings( 'tree' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'tree_1' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'tree_2' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'tree_3' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'tree_4' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'tree_5' ), 'tree_6' )
        self.assertEqual( self._tag_siblings_manager.GetSibling( 'tree_6' ), None )
        
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'tree_1' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'tree_2' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'tree_3' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'tree_4' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'tree_5' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.GetAllSiblings( 'tree_6' ) ), set( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) )
        
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'tree_1' ] ) ), set( [ 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'tree_1', 'tree_3', 'tree_5' ] ) ), set( [ 'tree_6' ] ) )
        self.assertEqual( set( self._tag_siblings_manager.CollapseTags( [ 'tree_1', 'tree_2', 'tree_3', 'tree_4', 'tree_5', 'tree_6' ] ) ), set( [ 'tree_6' ] ) )
        
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'tree_1' : 10 } ), { 'tree_6' : 10 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'tree_1' : 10, 'tree_3' : 5, 'tree_5' : 20 } ), { 'tree_6' : 35 } )
        self.assertEqual( self._tag_siblings_manager.CollapseTagsToCount( { 'tree_1' : 10, 'tree_2' : 3, 'tree_3' : 5, 'tree_4' : 2, 'tree_5' : 20, 'tree_6' : 30 } ), { 'tree_6' : 70 } )
        
    
if __name__ == '__main__':
    
    app = TestConstants.TestController()
    
    unittest.main( verbosity = 2, exit = False )
    
    raw_input()
    