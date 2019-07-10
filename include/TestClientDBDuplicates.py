from . import ClientConstants as CC
from . import ClientData
from . import ClientDB
from . import ClientDefaults
from . import ClientDownloading
from . import ClientExporting
from . import ClientFiles
from . import ClientGUIManagement
from . import ClientGUIPages
from . import ClientImporting
from . import ClientImportLocal
from . import ClientImportOptions
from . import ClientImportFileSeeds
from . import ClientRatings
from . import ClientSearch
from . import ClientServices
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusVideoHandling
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusSerialisable
import itertools
import os
from . import ServerDB
import shutil
import sqlite3
import stat
from . import TestController
import time
import threading
import unittest
import wx

class TestClientDBDuplicates( unittest.TestCase ):
    
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
        
        HG.test_controller.SetRead( 'hash_status', ( CC.STATUS_UNKNOWN, None, '' ) )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._delete_db()
        
    
    def _read( self, action, *args, **kwargs ): return TestClientDBDuplicates._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestClientDBDuplicates._db.Write( action, True, *args, **kwargs )
    
    def _get_group_potential_count( self, file_duplicate_types_to_counts ):
        
        num_potentials = len( self._all_hashes ) - 1
        
        num_potentials -= len( self._our_main_dupe_group_hashes ) - 1
        num_potentials -= len( self._our_second_dupe_group_hashes ) - 1
        num_potentials -= len( self._our_alt_dupe_group_hashes ) - 1
        num_potentials -= len( self._our_fp_dupe_group_hashes ) - 1
        
        if HC.DUPLICATE_FALSE_POSITIVE in file_duplicate_types_to_counts:
            
            # this would not work if the fp group had mutiple alt members
            num_potentials -= file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ]
            
        
        if HC.DUPLICATE_ALTERNATE in file_duplicate_types_to_counts:
            
            num_potentials -= file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ]
            
        
        return num_potentials
        
    
    def _import_and_find_dupes( self ):
        
        phash = os.urandom( 8 )
        
        # fake-import the files with the phash
        
        ( size, mime, width, height, duration, num_frames, num_words ) = ( 65535, HC.IMAGE_JPEG, 640, 480, None, None, None )
        
        for hash in self._all_hashes:
            
            fake_file_import_job = ClientImportFileSeeds.FileImportJob( 'fake path' )
            
            fake_file_import_job._hash = hash
            fake_file_import_job._file_info = ( size, mime, width, height, duration, num_frames, num_words )
            fake_file_import_job._extra_hashes = ( b'abcd', b'abcd', b'abcd' )
            fake_file_import_job._phashes = [ phash ]
            fake_file_import_job._file_import_options = ClientImportOptions.FileImportOptions()
            
            self._write( 'import_file', fake_file_import_job )
            
        
        # run search maintenance
        
        self._write( 'maintain_similar_files_tree' )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
    
    def _test_initial_state( self ):
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertEqual( num_potentials, self._expected_num_potentials )
        
        result = self._read( 'random_potential_duplicate_hashes', self._file_search_context, both_files_match )
        
        self.assertEqual( len( result ), len( self._all_hashes ) )
        
        self.assertEqual( set( result ), self._all_hashes )
        
        filtering_pairs = self._read( 'duplicate_pairs_for_filtering', self._file_search_context, both_files_match )
        
        for ( a, b ) in filtering_pairs:
            
            self.assertIn( a, self._all_hashes )
            self.assertIn( b, self._all_hashes )
            
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[0] )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 1 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[0], HC.DUPLICATE_POTENTIAL )
        
        self.assertEqual( result[0], self._dupe_hashes[0] )
        
        self.assertEqual( set( result ), self._all_hashes )
        
    
    def _test_initial_better_worse( self ):
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[1], {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[1] )
        
        row = ( HC.DUPLICATE_BETTER, self._dupe_hashes[1], self._dupe_hashes[2], {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[2] )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        self.assertEqual( num_potentials, self._expected_num_potentials )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[1] )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[2] )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[1], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[1], self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[1], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[1] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[2], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[2], self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[2], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[2] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def _test_initial_king_usurp( self ):
        
        self._old_king_hash = self._king_hash
        self._king_hash = self._dupe_hashes[3]
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._old_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._king_hash )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        self.assertEqual( num_potentials, self._expected_num_potentials )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._old_king_hash )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._old_king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._old_king_hash, self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._old_king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._old_king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def _test_initial_same_quality( self ):
        
        row = ( HC.DUPLICATE_SAME_QUALITY, self._king_hash, self._dupe_hashes[4], {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[4] )
        
        row = ( HC.DUPLICATE_SAME_QUALITY, self._old_king_hash, self._dupe_hashes[5], {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[5] )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        self.assertEqual( num_potentials, self._expected_num_potentials )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[4] )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[5] )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[4], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[4], self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[4], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[4] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[5], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[5], self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._dupe_hashes[5], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[5] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def _test_explicit_set_new_king( self ):
        
        self._write( 'duplicate_set_king', self._dupe_hashes[5] )
        
        self._king_hash = self._dupe_hashes[5]
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def _test_establish_second_group( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._second_group_king_hash, self._second_group_dupe_hashes[1], {} ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._second_group_king_hash, self._second_group_dupe_hashes[2], {} ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._second_group_king_hash, self._second_group_dupe_hashes[3], {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        self._our_second_dupe_group_hashes.add( self._second_group_dupe_hashes[1] )
        self._our_second_dupe_group_hashes.add( self._second_group_dupe_hashes[2] )
        self._our_second_dupe_group_hashes.add( self._second_group_dupe_hashes[3] )
        
    
    def _test_poach_better( self ):
        
        # better than not the king
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._second_group_dupe_hashes[1], {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_second_dupe_group_hashes.discard( self._second_group_dupe_hashes[1] )
        self._our_main_dupe_group_hashes.add( self._second_group_dupe_hashes[1] )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._second_group_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_second_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._second_group_king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._second_group_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._second_group_king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._second_group_king_hash )
        self.assertEqual( set( result ), self._our_second_dupe_group_hashes )
        
    
    def _test_poach_same( self ):
        
        # not the king is the same as not the king
        
        row = ( HC.DUPLICATE_SAME_QUALITY, self._old_king_hash, self._second_group_dupe_hashes[2], {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_second_dupe_group_hashes.discard( self._second_group_dupe_hashes[2] )
        self._our_main_dupe_group_hashes.add( self._second_group_dupe_hashes[2] )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._second_group_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_second_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._second_group_king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._second_group_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._second_group_king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._second_group_king_hash )
        self.assertEqual( set( result ), self._our_second_dupe_group_hashes )
        
    
    def _test_group_merge( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[6], self._dupe_hashes[7], {} ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[8], self._dupe_hashes[9], {} ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[10], self._dupe_hashes[11], {} ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[12], self._dupe_hashes[13], {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._old_king_hash, self._dupe_hashes[6], {} ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._king_hash, self._dupe_hashes[8], {} ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._old_king_hash, self._dupe_hashes[10], {} ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[12], {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_main_dupe_group_hashes.update( ( self._dupe_hashes[ i ] for i in range( 6, 14 ) ) )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def _test_establish_false_positive_group( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._false_positive_king_hash, self._similar_looking_false_positive_hashes[1], {} ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._false_positive_king_hash, self._similar_looking_false_positive_hashes[2], {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_fp_dupe_group_hashes.add( self._similar_looking_false_positive_hashes[1] )
        self._our_fp_dupe_group_hashes.add( self._similar_looking_false_positive_hashes[2] )
        
    
    def _test_false_positive( self ):
        
        row = ( HC.DUPLICATE_FALSE_POSITIVE, self._king_hash, self._false_positive_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 3 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._false_positive_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 3 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_fp_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_FALSE_POSITIVE )
        
        self.assertEqual( result, [ self._king_hash, self._false_positive_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._false_positive_king_hash, HC.DUPLICATE_FALSE_POSITIVE )
        
        self.assertEqual( result, [ self._false_positive_king_hash, self._king_hash ] )
        
    
    def _test_establish_alt_group( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._alternate_king_hash, self._similar_looking_alternate_hashes[1], {} ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._alternate_king_hash, self._similar_looking_alternate_hashes[2], {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_alt_dupe_group_hashes.add( self._similar_looking_alternate_hashes[1] )
        self._our_alt_dupe_group_hashes.add( self._similar_looking_alternate_hashes[2] )
        
    
    def _test_alt( self ):
        
        row = ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._alternate_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 5 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._alternate_king_hash, HC.DUPLICATE_POTENTIAL )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._alternate_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 5 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_alt_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_ALTERNATE )
        
        self.assertEqual( result, [ self._king_hash, self._alternate_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._alternate_king_hash, HC.DUPLICATE_ALTERNATE )
        
        self.assertEqual( result, [ self._alternate_king_hash, self._king_hash ] )
        
    
    def _test_expand_false_positive( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._false_positive_king_hash, self._similar_looking_false_positive_hashes[3], {} ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._false_positive_king_hash, self._similar_looking_false_positive_hashes[4], {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_fp_dupe_group_hashes.add( self._similar_looking_false_positive_hashes[3] )
        self._our_fp_dupe_group_hashes.add( self._similar_looking_false_positive_hashes[4] )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 5 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._false_positive_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 3 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_fp_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 2 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_FALSE_POSITIVE )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), { self._king_hash, self._false_positive_king_hash } )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._false_positive_king_hash, HC.DUPLICATE_FALSE_POSITIVE )
        
        self.assertEqual( result[0], self._false_positive_king_hash )
        self.assertEqual( set( result ), { self._false_positive_king_hash, self._king_hash, self._alternate_king_hash } )
        
    
    def _test_expand_alt( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._alternate_king_hash, self._similar_looking_alternate_hashes[3], {} ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._alternate_king_hash, self._similar_looking_alternate_hashes[4], {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        both_files_match = True
        
        num_potentials = self._read( 'potential_duplicates_count', self._file_search_context, both_files_match )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_alt_dupe_group_hashes.add( self._similar_looking_alternate_hashes[3] )
        self._our_alt_dupe_group_hashes.add( self._similar_looking_alternate_hashes[4] )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 5 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._alternate_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 5 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_alt_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash, HC.DUPLICATE_ALTERNATE )
        
        self.assertEqual( result, [ self._king_hash, self._alternate_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', CC.LOCAL_FILE_SERVICE_KEY, self._alternate_king_hash, HC.DUPLICATE_ALTERNATE )
        
        self.assertEqual( result, [ self._alternate_king_hash, self._king_hash ] )
        
    
    def _test_dissolve( self ):
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 5 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        # remove member
        
        self._write( 'remove_duplicates_member', ( self._dupe_hashes[7], ) )
        
        self._our_main_dupe_group_hashes.discard( self._dupe_hashes[7] )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 5 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        # clear fps
        
        self._write( 'clear_false_positive_relations', ( self._king_hash, ) )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 4 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        # remove alt
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._false_positive_king_hash, {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 4 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 2 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 2 )
        
        self._write( 'remove_alternates_member', ( self._false_positive_king_hash, ) )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 4 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        # dissolve alt
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._false_positive_king_hash, {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        self._write( 'dissolve_alternates_group', ( self._king_hash, ) )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 0 )
        
        # dissolve group
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[1], {} ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 1 )
        
        self._write( 'dissolve_duplicates_group', ( self._king_hash, ) )
        
        result = self._read( 'file_duplicate_info', CC.LOCAL_FILE_SERVICE_KEY, self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 0 )
        
    
    def test_duplicates( self ):
        
        self._dupe_hashes = [ HydrusData.GenerateKey() for i in range( 16 ) ]
        self._second_group_dupe_hashes = [ HydrusData.GenerateKey() for i in range( 4 ) ]
        self._similar_looking_alternate_hashes = [ HydrusData.GenerateKey() for i in range( 5 ) ]
        self._similar_looking_false_positive_hashes = [ HydrusData.GenerateKey() for i in range( 5 ) ]
        
        self._all_hashes = set()
        
        self._all_hashes.update( self._dupe_hashes )
        self._all_hashes.update( self._second_group_dupe_hashes )
        self._all_hashes.update( self._similar_looking_alternate_hashes )
        self._all_hashes.update( self._similar_looking_false_positive_hashes )
        
        self._king_hash = self._dupe_hashes[0]
        self._second_group_king_hash = self._second_group_dupe_hashes[0]
        self._false_positive_king_hash = self._similar_looking_false_positive_hashes[0]
        self._alternate_king_hash = self._similar_looking_alternate_hashes[0]
        
        self._our_main_dupe_group_hashes = set( [ self._king_hash ] )
        self._our_second_dupe_group_hashes = set( [ self._second_group_king_hash ] )
        self._our_alt_dupe_group_hashes = set( [ self._alternate_king_hash ] )
        self._our_fp_dupe_group_hashes = set( [ self._false_positive_king_hash ] )
        
        n = len( self._all_hashes )
        
        self._num_free_agents = n
        
        # initial number pair combinations is (n(n-1))/2
        self._expected_num_potentials = int( n * ( n - 1 ) / 2 )
        
        size_pred = ClientSearch.Predicate( HC.PREDICATE_TYPE_SYSTEM_SIZE, ( '=', 65535, HydrusData.ConvertUnitToInt( 'B' ) ) )
        
        self._file_search_context = ClientSearch.FileSearchContext( file_service_key = CC.LOCAL_FILE_SERVICE_KEY, predicates = [ size_pred ] )
        
        self._import_and_find_dupes()
        
        self._test_initial_state()
        
        self._test_initial_better_worse()
        self._test_initial_king_usurp()
        self._test_initial_same_quality()
        
        self._test_explicit_set_new_king()
        
        self._test_establish_second_group()
        self._test_poach_better()
        self._test_poach_same()
        self._test_group_merge()
        
        self._test_establish_false_positive_group()
        self._test_false_positive()
        
        self._test_establish_alt_group()
        self._test_alt()
        
        self._test_expand_false_positive()
        self._test_expand_alt()
        
        self._test_dissolve()
        
    
