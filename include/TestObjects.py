import ClientConstants
import collections
import HydrusConstants as HC
import TestConstants
import unittest

class TestTagSiblings( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._first = TestConstants.GenerateClientServiceIdentifier( HC.LOCAL_TAG )
        self._third = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        self._second = TestConstants.GenerateClientServiceIdentifier( HC.TAG_REPOSITORY )
        
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
        
        self._tag_siblings_manager = ClientConstants.TagSiblingsManager()
        
    
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
    