from . import ClientConstants as CC
from . import ClientThreading
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusGlobals as HG
import os
import threading
import time
import unittest

def do_read_job( rwlock, result_list, name ):
    
    with rwlock.read:
        
        result_list.append( 'begin read {}'.format( name ) )
        
        time.sleep( 0.25 )
        
        result_list.append( 'end read {}'.format( name ) )
        
    

def do_write_job( rwlock, result_list, name ):
    
    with rwlock.write:
        
        result_list.append( 'begin write {}'.format( name ) )
        
        time.sleep( 0.5 )
        
        result_list.append( 'end write {}'.format( name ) )
        
    

class TestFileRWLock( unittest.TestCase ):
    
    def test_simple( self ):
        
        rwlock = ClientThreading.FileRWLock()
        
        result_list = []
        
        do_read_job( rwlock, result_list, '1' )
        
        expected_result = []
        
        expected_result.extend( [ 'begin read 1', 'end read 1' ] )
        
        self.assertEqual( result_list, expected_result )
        
        #
        
        result_list = []
        
        do_write_job( rwlock, result_list, '1' )
        
        expected_result = []
        
        expected_result.extend( [ 'begin write 1', 'end write 1' ] )
        
        self.assertEqual( result_list, expected_result )
        
    
    def test_shared_read( self ):
        
        rwlock = ClientThreading.FileRWLock()
        
        result_list = []
        
        HG.test_controller.CallLater( 0.0, do_read_job, rwlock, result_list, '1' )
        HG.test_controller.CallLater( 0.1, do_read_job, rwlock, result_list, '2' )
        
        time.sleep( 0.2 )
        
        with rwlock.write:
            
            pass
            
        
        results = set( result_list )
        
        expected_results = set()
        
        expected_results.update( [ 'begin read 1', 'end read 1' ] )
        expected_results.update( [ 'begin read 2', 'end read 2' ] )
        
        self.assertEqual( results, expected_results )
        
        #
        
        result_list = []
        
        for i in range( 10 ):
            
            HG.test_controller.CallLater( 0.0, do_read_job, rwlock, result_list, str( i ) )
            
        
        time.sleep( 0.2 )
        
        with rwlock.write:
            
            pass
            
        
        expected_results = set()
        
        for i in range( 10 ):
            
            expected_results.update( [ 'begin read {}'.format( i ), 'end read {}'.format( i ) ] )
            
        
        results = set( result_list )
        
        self.assertEqual( results, expected_results )
        
    
    def test_competing_write( self ):
        
        rwlock = ClientThreading.FileRWLock()
        
        result_list = []
        
        HG.test_controller.CallLater( 0.0, do_write_job, rwlock, result_list, '1' )
        HG.test_controller.CallLater( 0.1, do_write_job, rwlock, result_list, '2' )
        
        time.sleep( 0.2 )
        
        with rwlock.read:
            
            pass
            
        
        expected_result = []
        
        expected_result.extend( [ 'begin write 1', 'end write 1' ] )
        expected_result.extend( [ 'begin write 2', 'end write 2' ] )
        
        self.assertEqual( result_list, expected_result )
        
        #
        
        result_list = []
        
        for i in range( 10 ):
            
            HG.test_controller.CallLater( 0.0, do_write_job, rwlock, result_list, str( i ) )
            
        
        time.sleep( 0.2 )
        
        with rwlock.read:
            
            pass
            
        
        expected_results = set()
        
        for i in range( 10 ):
            
            expected_pair = ( 'begin write {}'.format( i ), 'end write {}'.format( i ) )
            
            expected_results.add( expected_pair )
            
        
        for i in range( 10 ):
            
            result_pair = ( result_list[ i * 2 ], result_list[ ( i * 2 ) + 1 ] )
            
            self.assertIn( result_pair, expected_results )
            
        

    def test_mixed_competing( self ):
        
        rwlock = ClientThreading.FileRWLock()
        
        result_list = []
        
        all_expected_results = set()
        
        for i in range( 10 ):
            
            HG.test_controller.CallLater( 0.0 * i, do_read_job, rwlock, result_list, str( i ) )
            
            all_expected_results.update( [ 'begin read {}'.format( i ), 'end read {}'.format( i ) ] )
            
        
        for i in range( 5 ):
            
            HG.test_controller.CallLater( 0.0 * i, do_write_job, rwlock, result_list, str( i ) )
            
            all_expected_results.update( [ 'begin write {}'.format( i ), 'end write {}'.format( i ) ] )
            
        
        time.sleep( 0.2 )
        
        with rwlock.read:
            
            pass
            
        
        with rwlock.write:
            
            pass
            
        
        self.assertEqual( set( result_list ), all_expected_results )
        
        for i in range( 15 ):
            
            # even if reads mix up a bit, every two items should have the same read/write value
            
            a = result_list[ i * 2 ]
            b = result_list[ ( i * 2 ) + 1 ]
            
            if 'read' in a:
                
                self.assertIn( 'read', b )
                
            
            if 'write' in a:
                
                self.assertTrue( a.startswith( 'begin write' ) )
                self.assertTrue( b.startswith( 'end write' ) )
                
                self.assertEqual( a[-2:], b[-2:] )
                
            
        
