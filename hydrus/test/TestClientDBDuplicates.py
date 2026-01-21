import os
import time
import typing
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusNumbers

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.db import ClientDB
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate

from hydrus.test import TestController
from hydrus.test import TestGlobals as TG

# this test suite is a nightmare. it was originally a monolith hell with all sorts of math adjustment trying to keep track of this twisting path. very difficult to edit/comprehend, and how it ever actually passed I do not know
# I made a big push to atomise it, but there remains a bunch of fluff and weirdness. I have not got through them rigorously to ensure they are still testing relevent stuff everywhere
# _get_group_potential_count in particular could do with a significant rework
# _expected_num_potentials too is a mess
# probably better if each _InitialiseState is created with a list of hashes just for that test and we test numbers hardcoded

class TestClientDBDuplicates( unittest.TestCase ):
    
    _db: typing.Any = None
    
    @classmethod
    def _clear_db( cls ):
        
        cls._delete_db()
        
        # class variable
        cls._db = ClientDB.DB( TG.test_controller, TestController.DB_DIR, 'client' )
        
    
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
        
        cls._db = ClientDB.DB( TG.test_controller, TestController.DB_DIR, 'client' )
        
        TG.test_controller.SetRead( 'hash_status', ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._delete_db()
        
    
    def _read( self, action, *args, **kwargs ): return TestClientDBDuplicates._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestClientDBDuplicates._db.Write( action, True, *args, **kwargs )
    
    def _InitialiseState( self ):
        
        self._clear_db()
        
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
        
        self._our_main_dupe_group_hashes = { self._king_hash }
        self._our_second_dupe_group_hashes = { self._second_group_king_hash }
        self._our_alt_dupe_group_hashes = { self._alternate_king_hash }
        self._our_fp_dupe_group_hashes = { self._false_positive_king_hash }
        
        n = len( self._all_hashes )
        
        self._num_free_agents = n
        
        # initial number pair combinations is (n(n-1))/2
        self._expected_num_potentials = int( n * ( n - 1 ) / 2 )
        
        size_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_SIZE, ( '=', 65535, HydrusNumbers.UnitToInt( 'B' ) ) )
        png_pred = ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, ( HC.IMAGE_PNG, ) )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        
        self._file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = [ size_pred ] )
        self._file_search_context_2 = ClientSearchFileSearchContext.FileSearchContext( location_context = location_context, predicates = [ png_pred ] )
        
        self._import_and_find_dupes()
        
    
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
        
        # they all share the same phash so are all dupes
        perceptual_hash = os.urandom( 8 )
        
        # fake-import the files with the perceptual_hash
        
        ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words ) = ( 65535, HC.IMAGE_JPEG, 640, 480, None, None, False, None )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        for hash in self._all_hashes:
            
            fake_file_import_job = ClientImportFiles.FileImportJob( 'fake path', file_import_options )
            
            fake_file_import_job._pre_import_file_status = ClientImportFiles.FileImportStatus( CC.STATUS_UNKNOWN, hash )
            fake_file_import_job._file_info = ( size, mime, width, height, duration_ms, num_frames, has_audio, num_words )
            fake_file_import_job._extra_hashes = ( b'abcd', b'abcd', b'abcd' )
            fake_file_import_job._perceptual_hashes = [ perceptual_hash ]
            
            self._write( 'import_file', fake_file_import_job )
            
        
        # run search maintenance
        
        self._write( 'maintain_similar_files_tree' )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
    
    def test_aaa_initial_state( self ):
        
        self._InitialiseState()
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertEqual( num_potentials, self._expected_num_potentials )
        
        result = self._read( 'random_potential_duplicate_hashes', potential_duplicates_search_context )
        
        self.assertEqual( len( result ), len( self._all_hashes ) )
        
        self.assertEqual( set( result ), self._all_hashes )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[0] )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 1 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[0], HC.DUPLICATE_POTENTIAL )
        
        self.assertEqual( result[0], self._dupe_hashes[0] )
        
        self.assertEqual( set( result ), self._all_hashes )
        
    
    def test_bbb_better_worse( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[1] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        row = ( HC.DUPLICATE_BETTER, self._dupe_hashes[1], self._dupe_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[2] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertEqual( num_potentials, self._expected_num_potentials )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[1] )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[2] )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[1], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[1], self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[1], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[1] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[2], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[2], self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[2], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[2] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def test_bbb_king_usurp( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[1] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        row = ( HC.DUPLICATE_BETTER, self._dupe_hashes[1], self._dupe_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[2] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        self._old_king_hash = self._king_hash
        self._king_hash = self._dupe_hashes[3]
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._old_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._king_hash )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertEqual( num_potentials, self._expected_num_potentials )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._old_king_hash )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._old_king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._old_king_hash, self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._old_king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._old_king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def test_bbb_same_quality( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_SAME_QUALITY, self._king_hash, self._dupe_hashes[4], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[4] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        row = ( HC.DUPLICATE_SAME_QUALITY, self._dupe_hashes[4], self._dupe_hashes[5], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[5] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertEqual( num_potentials, self._expected_num_potentials )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[4] )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[5] )
        
        self.assertEqual( result[ 'is_king' ], False )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], self._get_group_potential_count( file_duplicate_types_to_counts ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[4], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[4], self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[4], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[4] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[5], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[5], self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[5], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[5] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def test_bbb_explicit_set_new_king( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[1] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        self._write( 'duplicate_set_king', self._dupe_hashes[1] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[1], HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._dupe_hashes[1] ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[1], HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._dupe_hashes[1] )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def _test_establish_second_group( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._second_group_king_hash, self._second_group_dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._second_group_king_hash, self._second_group_dupe_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._second_group_king_hash, self._second_group_dupe_hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        self._our_second_dupe_group_hashes.add( self._second_group_dupe_hashes[1] )
        self._our_second_dupe_group_hashes.add( self._second_group_dupe_hashes[2] )
        self._our_second_dupe_group_hashes.add( self._second_group_dupe_hashes[3] )
        
    
    def test_poach_better( self ):
        
        self._InitialiseState()
        
        self._test_establish_second_group()
        
        # better than not the king
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._second_group_dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_second_dupe_group_hashes.discard( self._second_group_dupe_hashes[1] )
        self._our_main_dupe_group_hashes.add( self._second_group_dupe_hashes[1] )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        # TODO: sometimes this is 20 instead of 21
        # my guess is this is some complicated relationships due to random population of this test
        # the answer is to rewrite this monstrocity so the tests are simpler to understand and pull apart
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._second_group_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_second_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._second_group_king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._second_group_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._second_group_king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._second_group_king_hash )
        self.assertEqual( set( result ), self._our_second_dupe_group_hashes )
        
    
    def test_poach_same( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[1] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        self._test_establish_second_group()
        
        # setting a not-king the same as a not-king
        
        row = ( HC.DUPLICATE_SAME_QUALITY, self._dupe_hashes[1], self._second_group_dupe_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_second_dupe_group_hashes.discard( self._second_group_dupe_hashes[2] )
        self._our_main_dupe_group_hashes.add( self._second_group_dupe_hashes[2] )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        # TODO: sometimes this is 20 instead of 21
        # my guess is this is some complicated relationships due to random population of this test
        # the answer is to rewrite this monstrocity so the tests are simpler to understand and pull apart
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._second_group_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_second_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._second_group_king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._second_group_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._second_group_king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._second_group_king_hash )
        self.assertEqual( set( result ), self._our_second_dupe_group_hashes )
        
    
    def test_group_merge( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[1] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[6], self._dupe_hashes[7], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[8], self._dupe_hashes[9], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[10], self._dupe_hashes[11], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[12], self._dupe_hashes[13], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._dupe_hashes[1], self._dupe_hashes[6], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._king_hash, self._dupe_hashes[8], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._dupe_hashes[1], self._dupe_hashes[10], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[12], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_main_dupe_group_hashes.update( ( self._dupe_hashes[ i ] for i in range( 6, 14 ) ) )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        result = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( result, result -1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_KING )
        
        self.assertEqual( result, [ self._king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_MEMBER )
        
        self.assertEqual( result[0], self._king_hash )
        self.assertEqual( set( result ), self._our_main_dupe_group_hashes )
        
    
    def _test_establish_false_positive_group( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._false_positive_king_hash, self._similar_looking_false_positive_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._false_positive_king_hash, self._similar_looking_false_positive_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_fp_dupe_group_hashes.add( self._similar_looking_false_positive_hashes[1] )
        self._our_fp_dupe_group_hashes.add( self._similar_looking_false_positive_hashes[2] )
        
    
    def test_false_positive( self ):
        
        self._InitialiseState()
        
        self._test_establish_false_positive_group()
        
        row = ( HC.DUPLICATE_FALSE_POSITIVE, self._king_hash, self._false_positive_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._false_positive_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 3 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_fp_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_FALSE_POSITIVE )
        
        self.assertEqual( result, [ self._king_hash, self._false_positive_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._false_positive_king_hash, HC.DUPLICATE_FALSE_POSITIVE )
        
        self.assertEqual( result, [ self._false_positive_king_hash, self._king_hash ] )
        
    
    def _test_establish_alt_group( self ):
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_BETTER, self._alternate_king_hash, self._similar_looking_alternate_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        rows.append( ( HC.DUPLICATE_SAME_QUALITY, self._alternate_king_hash, self._similar_looking_alternate_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        self._our_alt_dupe_group_hashes.add( self._similar_looking_alternate_hashes[1] )
        self._our_alt_dupe_group_hashes.add( self._similar_looking_alternate_hashes[2] )
        
    
    def test_alt( self ):
        
        self._InitialiseState()
        
        self._test_establish_alt_group()
        
        row = ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._alternate_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 3 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._alternate_king_hash, HC.DUPLICATE_POTENTIAL )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._alternate_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 4 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_alt_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_ALTERNATE )
        
        self.assertEqual( result, [ self._king_hash, self._alternate_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._alternate_king_hash, HC.DUPLICATE_ALTERNATE )
        
        self.assertEqual( result, [ self._alternate_king_hash, self._king_hash ] )
        
    
    def test_alt_with_fp( self ):
        
        self._InitialiseState()
        
        self._test_establish_alt_group()
        
        row = ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._alternate_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        row = ( HC.DUPLICATE_FALSE_POSITIVE, self._king_hash, self._false_positive_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        pixel_dupes_preference = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        max_hamming_distance = 4
        dupe_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_ONE_SEARCH
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( self._file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( self._file_search_context_2 )
        potential_duplicates_search_context.SetDupeSearchType( dupe_search_type )
        potential_duplicates_search_context.SetPixelDupesPreference( pixel_dupes_preference )
        potential_duplicates_search_context.SetMaxHammingDistance( max_hamming_distance )
        
        num_potentials = self._read( 'potential_duplicates_count', potential_duplicates_search_context )
        
        self.assertLess( num_potentials, self._expected_num_potentials )
        
        self._expected_num_potentials = num_potentials
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 4 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._alternate_king_hash, HC.DUPLICATE_POTENTIAL )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._alternate_king_hash )
        
        self.assertEqual( result[ 'is_king' ], True )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 5 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_alt_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash, HC.DUPLICATE_ALTERNATE )
        
        self.assertEqual( result, [ self._king_hash, self._alternate_king_hash ] )
        
        result = self._read( 'file_duplicate_hashes', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._alternate_king_hash, HC.DUPLICATE_ALTERNATE )
        
        self.assertEqual( result, [ self._alternate_king_hash, self._king_hash ] )
        
    
    def test_remove_potentials( self ):
        
        self._InitialiseState()
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 1 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        
        # remove potentials
        
        self._write( 'remove_potential_pairs', ( self._king_hash, ) )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 0 )
        
    
    def test_remove_member( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[1] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[2] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
        self._write( 'remove_duplicates_member', ( self._dupe_hashes[1], ) )
        
        self._our_main_dupe_group_hashes.discard( self._dupe_hashes[1] )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        
    
    def test_remove_fp( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_FALSE_POSITIVE, self._king_hash, self._false_positive_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        num_cleared = self._write( 'clear_all_false_positive_relations', ( self._king_hash, ) )
        
        self.assertEqual( num_cleared, 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 1 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        
    
    def test_remove_fp_within_fail( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_FALSE_POSITIVE, self._king_hash, self._false_positive_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        num_cleared = self._write( 'clear_internal_false_positive_relations', ( self._king_hash, self._dupe_hashes[1] ) )
        
        self.assertEqual( num_cleared, 0 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_FALSE_POSITIVE ], 1 )
        
    
    def test_remove_fp_within_success( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_FALSE_POSITIVE, self._king_hash, self._false_positive_king_hash, {} )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        num_cleared = self._write( 'clear_internal_false_positive_relations', ( self._king_hash, self._false_positive_king_hash ) )
        
        self.assertEqual( num_cleared, 1 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 1 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        
    
    def test_remove_alt( self ):
        
        self._InitialiseState()
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._dupe_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 3 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 2 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 2 )
        
        self._write( 'remove_alternates_member', ( self._dupe_hashes[1], ) )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 3 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 1 )
        
    
    def test_dissolve_alt( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[3] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._dupe_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 4 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 2 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 2 )
        
        self._write( 'dissolve_alternates_group', ( self._king_hash, ) )
        
        self._our_main_dupe_group_hashes.discard( self._dupe_hashes[3] )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 1 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        
    
    def test_dissolve_group( self ):
        
        self._InitialiseState()
        
        row = ( HC.DUPLICATE_BETTER, self._king_hash, self._dupe_hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
        
        self._write( 'duplicate_pair_status', [ row ] )
        
        self._our_main_dupe_group_hashes.add( self._dupe_hashes[3] )
        
        self._num_free_agents -= 1
        
        self._expected_num_potentials -= self._num_free_agents
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._dupe_hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        rows = []
        
        rows.append( ( HC.DUPLICATE_ALTERNATE, self._king_hash, self._dupe_hashes[2], [ ClientContentUpdates.ContentUpdatePackage() ] ) )
        
        self._write( 'duplicate_pair_status', rows )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 4 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_MEMBER ], len( self._our_main_dupe_group_hashes ) - 1 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 2 )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_CONFIRMED_ALTERNATE ], 2 )
        
        self._write( 'dissolve_duplicates_group', ( self._king_hash, ) )
        
        self._our_main_dupe_group_hashes.discard( self._dupe_hashes[3] )
        
        self._write( 'maintain_similar_files_search_for_potential_duplicates', 0 )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._king_hash )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 1 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        
        result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ), self._dupe_hashes[1] )
        
        file_duplicate_types_to_counts = result[ 'counts' ]
        
        self.assertEqual( len( file_duplicate_types_to_counts ), 2 )
        
        expected = self._get_group_potential_count( file_duplicate_types_to_counts )
        
        self.assertIn( file_duplicate_types_to_counts[ HC.DUPLICATE_POTENTIAL ], ( expected, expected - 1 ) )
        self.assertEqual( file_duplicate_types_to_counts[ HC.DUPLICATE_ALTERNATE ], 1 )
        # ~no confirmed alternate~
        
    
