import random
import unittest

from hydrus.core import HydrusLists
from hydrus.core import HydrusNumbers

class TestHydrusNumbers( unittest.TestCase ):
    
    def test_ordinals( self ):
        
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 1 ), '1st' )
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 2 ), '2nd' )
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 3 ), '3rd' )
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 4 ), '4th' )
        
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 11 ), '11th' )
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 12 ), '12th' )
        
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 213 ), '213th' )
        
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 1011 ), '1,011th' )
        
    

class TestHydrusLists( unittest.TestCase ):
    
    def test_unique_fast_list( self ):
        
        def test_list_indices( some_list: HydrusLists.FastIndexUniqueList ):
            
            new_list = list( some_list )
            
            for ( index, value ) in enumerate( new_list ):
                
                self.assertEqual( some_list[ index ], value )
                
            
            
        
        def test_list( some_list: HydrusLists.FastIndexUniqueList ):
            
            test_list_indices( some_list )
            
            #
            
            some_list.sort( key = lambda o: random.random() )
            
            test_list_indices( some_list )
            
            #
            
            l = sorted( some_list )
            some_list.sort( key = lambda o: o )
            
            self.assertEqual( some_list, l )
            
            test_list_indices( some_list )
            
            #
            
            l = sorted( some_list, reverse = True )
            
            some_list.sort( key = lambda o: o, reverse = True )
            
            self.assertEqual( some_list, l )
            
            test_list_indices( some_list )
            
        
        l = HydrusLists.FastIndexUniqueList()
        
        l.append( 1 )
        
        self.assertIn( 1, l )
        self.assertNotIn( 2, l )
        self.assertEqual( len( l ), 1 )
        
        l.append( 2 )
        
        self.assertIn( 1, l )
        self.assertIn( 2, l )
        self.assertEqual( len( l ), 2 )
        
        test_list( l )
        
        #
        
        some_numbers = random.sample( range( 100 ), 30 )
        
        l = HydrusLists.FastIndexUniqueList( initial_items = some_numbers )
        
        test_list( l )
        
        #
        
        l.sort( key = lambda o: random.random() )
        l_copy = HydrusLists.FastIndexUniqueList( initial_items = l )
        
        for ( i1, i2 ) in zip( l, l_copy ):
            
            self.assertEqual( i1, i2 )
            self.assertEqual( l.index( i1 ), l_copy.index( i1 ) )
            
        
        test_list( l )
        test_list( l_copy )
        
        #
        
        removees_1 = random.sample( l, 10 )
        
        for n in removees_1:
            
            index = l.index( n )
            
            del l[ index ]
            
        
        expected_result_set = set( some_numbers ).difference( removees_1 )
        
        self.assertEqual( set( l ).intersection( expected_result_set ), expected_result_set )
        self.assertEqual( set( l ).intersection( removees_1 ), set() )
        
        test_list( l )
        
        expected_result_set.discard( l[-1] )
        
        del l[-1]
        
        test_list( l )
        
        removees_2 = random.sample( l, 10 )
        
        l.remove_items( removees_2 )
        
        expected_result_set.difference_update( removees_2 )
        
        self.assertEqual( set( l ).intersection( expected_result_set ), expected_result_set )
        self.assertEqual( set( l ).intersection( removees_2 ), set() )
        
        test_list( l )
        
    
