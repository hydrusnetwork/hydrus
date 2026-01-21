import os
import time
import typing
import unittest

from unittest import mock

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.db import ClientDB
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.duplicates import ClientDuplicatesAutoResolution
from hydrus.client.duplicates import ClientDuplicatesAutoResolutionComparators
from hydrus.client.importing import ClientImportFiles
from hydrus.client.importing.options import FileImportOptionsLegacy
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientMetadataConditional
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import TestController
from hydrus.test import TestGlobals as TG

class TestClientDBDuplicatesAutoResolution( unittest.TestCase ):
    
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
        
    
    def _do_resolution_work( self, rule ):
        
        media_result_pair = self._read( 'duplicates_auto_resolution_resolution_pair', rule )
        
        while media_result_pair is not None:
            
            ( media_result_1, media_result_2 ) = media_result_pair
            
            # this is the high CPU bit and needs to be out of the db
            # we used to have a nice embedded db call that looped and could clear hundreds of null pairs in one transaction, but it relied on db-side testing
            # maybe we could have two calls, for a known fast test somehow, but let's KISS from the other direction and simply regret the overhead
            result = rule.TestPair( media_result_1, media_result_2 )
            
            if result is None:
                
                self._write( 'duplicates_auto_resolution_commit_resolution_pair_failed', rule, media_result_pair )
                
            else:
                
                self._write( 'duplicates_auto_resolution_commit_resolution_pair_passed', rule, result )
                
            
            next_media_result_pair = self._read( 'duplicates_auto_resolution_resolution_pair', rule )
            
            if next_media_result_pair == media_result_pair:
                
                raise Exception( 'Resolution Work failed to clear a pair!' )
                
            
            media_result_pair = next_media_result_pair
            
        
    
    def _read( self, action, *args, **kwargs ): return TestClientDBDuplicatesAutoResolution._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestClientDBDuplicatesAutoResolution._db.Write( action, True, *args, **kwargs )
    
    def _compare_counts_cache( self, counts_cache_as_read, counts_we_expect ):
        
        for duplicate_status in [
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED,
            ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED
        ]:
            
            if duplicate_status in counts_we_expect:
                
                self.assertEqual( counts_cache_as_read[ duplicate_status ], counts_we_expect[ duplicate_status ] )
                
            else:
                
                self.assertEqual( counts_cache_as_read[ duplicate_status ], 0 )
                
            
        
    
    def _import_four_files( self ):
        
        hashes = []
        
        test_files = []
        
        test_files.append( ( 'muh_jpg.jpg', '5d884d84813beeebd59a35e474fa3e4742d0f2b6679faa7609b245ddbbd05444' ) )
        test_files.append( ( 'muh_png.png', 'cdc67d3b377e6e1397ffa55edc5b50f6bdf4482c7a6102c6f27fa351429d6f49' ) )
        test_files.append( ( 'muh_apng.png', '9e7b8b5abc7cb11da32db05671ce926a2a2b701415d1b2cb77a28deea51010c3' ) )
        test_files.append( ( 'muh_gif.gif', '00dd9e9611ebc929bfc78fde99a0c92800bbb09b9d18e0946cea94c099b211c2' ) )
        
        file_import_options = FileImportOptionsLegacy.FileImportOptionsLegacy()
        file_import_options.SetIsDefault( True )
        
        for ( filename, hex_hash ) in test_files:
            
            TG.test_controller.SetRead( 'hash_status', ClientImportFiles.FileImportStatus.STATICGetUnknownStatus() )
            
            path = HydrusStaticDir.GetStaticPath( os.path.join( 'testing', filename ) )
            
            hash = bytes.fromhex( hex_hash )
            
            hashes.append( hash )
            
            file_import_job = ClientImportFiles.FileImportJob( path, file_import_options )
            
            file_import_job.GeneratePreImportHashAndStatus()
            
            file_import_job.GenerateInfo()
            
            file_import_status = self._write( 'import_file', file_import_job )
            
        
        return hashes
        
    
    def test_editing_rules( self ):
        
        def compare_rule_lists( r_l_1, r_l_2 ):
            
            self.assertEqual( { rule.DumpToString() for rule in r_l_1 }, { rule.DumpToString() for rule in r_l_1 } )
            
        
        self._clear_db()
        
        rule_1 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 1' )
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC )
        
        rules_we_are_setting = [ rule_1.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self.assertTrue( rule_1_read.GetId() > 0 )
        
        rule_1.SetId( rule_1_read.GetId() )
        
        compare_rule_lists( rules_we_read, rules_we_are_setting )
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), {} )
        
        rule_2 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 2' )
        
        rule_2.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC )
        
        rules_we_are_setting = [ rule_1.Duplicate(), rule_2.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_2_read = [ rule for rule in rules_we_read if rule.GetId() not in ( -1, rule_1.GetId() ) ][0]
        
        self.assertTrue( rule_2_read.GetId() > 0 )
        self.assertNotEqual( rule_1.GetId(), rule_2.GetId() )
        
        rule_2.SetId( rule_2_read.GetId() )
        
        compare_rule_lists( rules_we_read, rules_we_are_setting )
        
        self._compare_counts_cache( rule_2_read.GetCountsCacheDuplicate(), {} )
        
        rule_2.SetName( 'test 2a' )
        
        rules_we_are_setting = [ rule_2.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        compare_rule_lists( rules_we_read, rules_we_are_setting )
        
        rule_3 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 3' )
        
        rule_3.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC )
        
        rules_we_are_setting = [ rule_2.Duplicate(), rule_3.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_3_read = [ rule for rule in rules_we_read if rule.GetId() > 0 and rule.GetId() != rule_2.GetId() ][0]
        
        self.assertTrue( rule_3_read.GetId() > 0 )
        self.assertNotEqual( rule_1.GetId(), rule_3.GetId() )
        
        rule_3.SetId( rule_3_read.GetId() )
        
        compare_rule_lists( rules_we_read, rules_we_are_setting )
        
        self._compare_counts_cache( rule_3_read.GetCountsCacheDuplicate(), {} )
        
    
    def test_editing_rules_resets_queues_search_change( self ):
        
        self._clear_db()
        
        rule_1 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 1' )
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING )
        ]
        
        file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
            location_context = location_context,
            predicates = predicates
        )
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( file_search_context_1 )
        potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
        potential_duplicates_search_context.SetMaxHammingDistance( 8 )
        
        rule_1.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        rule_1.SetPairSelector( selector )
        
        rules_we_are_setting = [ rule_1.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        hashes = self._import_four_files()
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ),
                ( HC.DUPLICATE_POTENTIAL, hashes[2], hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        self._write( 'duplicates_auto_resolution_do_search_work', rule_1_read )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 2 } )
        
        self._do_resolution_work( rule_1_read )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
        rule_1 = rule_1_read.Duplicate()
        
        potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_REQUIRED )
        
        rule_1.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
        
        rules_we_are_setting = [ rule_1 ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 2 } )
        
    
    def test_editing_rules_resets_queues_selector_change( self ):
        
        self._clear_db()
        
        rule_1 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 1' )
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING )
        ]
        
        file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
            location_context = location_context,
            predicates = predicates
        )
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( file_search_context_1 )
        potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
        potential_duplicates_search_context.SetMaxHammingDistance( 8 )
        
        rule_1.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        rule_1.SetPairSelector( selector )
        
        rules_we_are_setting = [ rule_1.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        hashes = self._import_four_files()
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ),
                ( HC.DUPLICATE_POTENTIAL, hashes[2], hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        self._write( 'duplicates_auto_resolution_do_search_work', rule_1_read )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 2 } )
        
        self._do_resolution_work( rule_1_read )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
        rule_1 = rule_1_read.Duplicate()
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_PNG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        rule_1.SetPairSelector( selector )
        
        rules_we_are_setting = [ rule_1 ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 2 } )
        
    
    def test_editing_rules_resets_queues_semi_to_fully( self ):
        
        self._clear_db()
        
        rule_1 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 1' )
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING )
        ]
        
        file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
            location_context = location_context,
            predicates = predicates
        )
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( file_search_context_1 )
        potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
        potential_duplicates_search_context.SetMaxHammingDistance( 8 )
        
        rule_1.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        rule_1.SetPairSelector( selector )
        
        rules_we_are_setting = [ rule_1.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        hashes = self._import_four_files()
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ),
                ( HC.DUPLICATE_POTENTIAL, hashes[2], hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        self._write( 'duplicates_auto_resolution_do_search_work', rule_1_read )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 2 } )
        
        self._do_resolution_work( rule_1_read )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
        rule_1 = rule_1_read.Duplicate()
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC )
        
        rules_we_are_setting = [ rule_1 ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
    
    def test_rules_sync_to_pairs( self ):
        
        self._clear_db()
        
        hashes = self._import_four_files()
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        rule_1 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 1' )
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC )
        
        rules_we_are_setting = [ rule_1.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 1 } )
        
        #
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[2], hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 2 } )
        
        #
        
        self._write( 'remove_potential_pairs', ( hashes[0], ) )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 1 } )
        
        #
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 2 } )
        
        #
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_BETTER, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 1 } )
        
    
    def test_rules_search( self ):
        
        # two pairs, and our search gets one
        
        self._clear_db()
        
        hashes = self._import_four_files()
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ),
                ( HC.DUPLICATE_POTENTIAL, hashes[2], hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        rule_1 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 1' )
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = ( HC.IMAGE_JPEG, ) )
        ]
        
        file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
            location_context = location_context,
            predicates = predicates
        )
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( file_search_context_1 )
        potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
        potential_duplicates_search_context.SetMaxHammingDistance( 8 )
        
        rule_1.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
        
        rules_we_are_setting = [ rule_1.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 2 } )
        
        ( still_work_to_do_here, matching_pairs_produced_here ) = self._write( 'duplicates_auto_resolution_do_search_work', rule_1_read )
        
        self.assertFalse( still_work_to_do_here )
        self.assertTrue( matching_pairs_produced_here )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_DOES_NOT_MATCH_SEARCH : 1 } )
        
    
    def test_rules_auto_resolution( self ):
        
        # two pairs, and our search gets both, and then we resolve one
        
        self._clear_db()
        
        hashes = self._import_four_files()
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ),
                ( HC.DUPLICATE_POTENTIAL, hashes[2], hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        rule_1 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 1' )
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_FULLY_AUTOMATIC )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING )
        ]
        
        file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
            location_context = location_context,
            predicates = predicates
        )
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( file_search_context_1 )
        potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
        potential_duplicates_search_context.SetMaxHammingDistance( 8 )
        
        rule_1.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        rule_1.SetPairSelector( selector )
        
        rule_1.SetAction( HC.DUPLICATE_BETTER )
        
        rules_we_are_setting = [ rule_1.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 2 } )
        
        ( still_work_to_do_here, matching_pairs_produced_here ) = self._write( 'duplicates_auto_resolution_do_search_work', rule_1_read )
        
        self.assertFalse( still_work_to_do_here )
        self.assertTrue( matching_pairs_produced_here )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 2 } )
        
        self._do_resolution_work( rule_1_read )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
        for ( hash, is_king, dupe_counts ) in [
            ( hashes[0], True, { HC.DUPLICATE_MEMBER : 1 } ),
            ( hashes[1], False, { HC.DUPLICATE_MEMBER : 1 } ),
            ( hashes[2], True, { HC.DUPLICATE_POTENTIAL : 1 } ),
            ( hashes[3], True, { HC.DUPLICATE_POTENTIAL : 1 } )
        ]:
            
            result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ), hash )
            
            self.assertEqual( result[ 'is_king' ], is_king )
            
            self._compare_counts_cache( result[ 'counts' ], dupe_counts )
            
        
        actioned_pairs_with_info = self._read( 'duplicates_auto_resolution_actioned_pairs', rule_1_read )
        
        ( media_result_1, media_result_2, duplicate_type, timestamp_ms ) = actioned_pairs_with_info[0]
        
        self.assertEqual( media_result_1.GetHash(), hashes[0] )
        self.assertEqual( media_result_2.GetHash(), hashes[1] )
        self.assertEqual( duplicate_type, HC.DUPLICATE_BETTER )
        
    
    def _semi_resolution_setup( self ):
        
        self._clear_db()
        
        hashes = self._import_four_files()
        
        self._write(
            'duplicate_pair_status',
            [
                ( HC.DUPLICATE_POTENTIAL, hashes[0], hashes[1], [ ClientContentUpdates.ContentUpdatePackage() ] ),
                ( HC.DUPLICATE_POTENTIAL, hashes[2], hashes[3], [ ClientContentUpdates.ContentUpdatePackage() ] )
            ]
        )
        
        rule_1 = ClientDuplicatesAutoResolution.DuplicatesAutoResolutionRule( 'test 1' )
        
        rule_1.SetOperationMode( ClientDuplicatesAutoResolution.DUPLICATES_AUTO_RESOLUTION_RULE_OPERATION_MODE_WORK_BUT_NO_ACTION )
        
        location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        predicates = [
            ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING )
        ]
        
        file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext(
            location_context = location_context,
            predicates = predicates
        )
        
        potential_duplicates_search_context = ClientPotentialDuplicatesSearchContext.PotentialDuplicatesSearchContext()
        
        potential_duplicates_search_context.SetFileSearchContext1( file_search_context_1 )
        potential_duplicates_search_context.SetFileSearchContext2( file_search_context_1 )
        potential_duplicates_search_context.SetDupeSearchType( ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH )
        potential_duplicates_search_context.SetPixelDupesPreference( ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED )
        potential_duplicates_search_context.SetMaxHammingDistance( 8 )
        
        rule_1.SetPotentialDuplicatesSearchContext( potential_duplicates_search_context )
        
        selector = ClientDuplicatesAutoResolutionComparators.PairSelector()
        
        comparator = ClientDuplicatesAutoResolutionComparators.PairComparatorOneFile()
        
        mc = ClientMetadataConditional.MetadataConditional()
        
        file_search_context = ClientSearchFileSearchContext.FileSearchContext(
            ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ),
            ClientSearchTagContext.TagContext(),
            predicates = [
                ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_MIME, value = { HC.IMAGE_JPEG } )
            ]
        )
        
        mc.SetFileSearchContext( file_search_context )
        
        comparator.SetMetadataConditional( mc )
        
        selector.SetComparators( [ comparator ] )
        
        rule_1.SetPairSelector( selector )
        
        rules_we_are_setting = [ rule_1.Duplicate() ]
        
        self._write( 'duplicates_auto_resolution_set_rules', rules_we_are_setting )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 2 } )
        
        ( still_work_to_do_here, matching_pairs_produced_here ) = self._write( 'duplicates_auto_resolution_do_search_work', rule_1_read )
        
        self.assertFalse( still_work_to_do_here )
        self.assertTrue( matching_pairs_produced_here )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_BUT_NOT_TESTED : 2 } )
        
        self._do_resolution_work( rule_1_read )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_PASSED_TEST_READY_TO_ACTION : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
        for ( hash, is_king, dupe_counts ) in [
            ( hashes[0], True, { HC.DUPLICATE_POTENTIAL : 1 } ),
            ( hashes[1], True, { HC.DUPLICATE_POTENTIAL : 1 } ),
            ( hashes[2], True, { HC.DUPLICATE_POTENTIAL : 1 } ),
            ( hashes[3], True, { HC.DUPLICATE_POTENTIAL : 1 } )
        ]:
            
            result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ), hash )
            
            self.assertEqual( result[ 'is_king' ], is_king )
            
            self._compare_counts_cache( result[ 'counts' ], dupe_counts )
            
        
        return hashes
        
    
    def test_rules_semi_resolution_approve( self ):
        
        # two pairs, and our search gets both, and one tests ok--we approve it
        
        hashes = self._semi_resolution_setup()
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        pending_action_pairs = self._read( 'duplicates_auto_resolution_pending_action_pairs', rule_1_read )
        
        [ ( media_result_1, media_result_2 ) ] = pending_action_pairs
        
        self._write( 'duplicates_auto_resolution_approve_pending_pairs', rule_1_read, [ ( media_result_1, media_result_2 ) ] )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_ACTIONED : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
        for ( hash, is_king, dupe_counts ) in [
            ( hashes[0], True, { HC.DUPLICATE_MEMBER : 1 } ),
            ( hashes[1], False, { HC.DUPLICATE_MEMBER : 1 } ),
            ( hashes[2], True, { HC.DUPLICATE_POTENTIAL : 1 } ),
            ( hashes[3], True, { HC.DUPLICATE_POTENTIAL : 1 } )
        ]:
            
            result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ), hash )
            
            self.assertEqual( result[ 'is_king' ], is_king )
            
            self._compare_counts_cache( result[ 'counts' ], dupe_counts )
            
        
        actioned_pairs_with_info = self._read( 'duplicates_auto_resolution_actioned_pairs', rule_1_read )
        
        ( media_result_1, media_result_2, duplicate_type, timestamp_ms ) = actioned_pairs_with_info[0]
        
        self.assertEqual( media_result_1.GetHash(), hashes[0] )
        self.assertEqual( media_result_2.GetHash(), hashes[1] )
        self.assertEqual( duplicate_type, HC.DUPLICATE_BETTER )
        
    
    def test_rules_semi_resolution_deny( self ):
        
        # two pairs, and our search gets both, and one tests ok--we deny it
        
        hashes = self._semi_resolution_setup()
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        pending_action_pairs = self._read( 'duplicates_auto_resolution_pending_action_pairs', rule_1_read )
        
        [ ( media_result_1, media_result_2 ) ] = pending_action_pairs
        
        self._write( 'duplicates_auto_resolution_deny_pending_pairs', rule_1_read, [ ( media_result_1, media_result_2 ) ] )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DENIED : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
        for ( hash, is_king, dupe_counts ) in [
            ( hashes[0], True, { HC.DUPLICATE_POTENTIAL : 1 } ),
            ( hashes[1], True, { HC.DUPLICATE_POTENTIAL : 1 } ),
            ( hashes[2], True, { HC.DUPLICATE_POTENTIAL : 1 } ),
            ( hashes[3], True, { HC.DUPLICATE_POTENTIAL : 1 } )
        ]:
            
            result = self._read( 'file_duplicate_info', ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ), hash )
            
            self.assertEqual( result[ 'is_king' ], is_king )
            
            self._compare_counts_cache( result[ 'counts' ], dupe_counts )
            
        
        actioned_pairs_with_info = self._read( 'duplicates_auto_resolution_actioned_pairs', rule_1_read )
        
        self.assertEqual( actioned_pairs_with_info, [] )
        
    
    def test_rules_semi_resolution_deny_fetch_and_rescind( self ):
        
        # two pairs, and our search gets both, and one tests ok--we deny it
        
        hashes = self._semi_resolution_setup()
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        pending_action_pairs = self._read( 'duplicates_auto_resolution_pending_action_pairs', rule_1_read )
        
        [ ( media_result_1, media_result_2 ) ] = pending_action_pairs
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = 123456 ):
            
            self._write( 'duplicates_auto_resolution_deny_pending_pairs', rule_1_read, [ ( media_result_1, media_result_2 ) ] )
            
            rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
            
            rule_1_read = rules_we_read[0]
            
            self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_USER_DENIED : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
            
            #
            
            denied_pairs_with_info = self._read( 'duplicates_auto_resolution_denied_pairs', rule_1_read )
            
            [ ( read_media_result_smaller, read_media_result_larger, timestamp_ms ) ] = denied_pairs_with_info
            
            self.assertEqual( { read_media_result_smaller, read_media_result_larger }, { media_result_1, media_result_2 } )
            self.assertTrue( timestamp_ms, 123456 )
            
        
        #
        
        self._write( 'duplicates_auto_resolution_rescind_denied_pairs', rule_1_read, [ ( media_result_1, media_result_2 ) ] )
        
        rules_we_read = self._read( 'duplicates_auto_resolution_rules_with_counts' )
        
        rule_1_read = rules_we_read[0]
        
        self._compare_counts_cache( rule_1_read.GetCountsCacheDuplicate(), { ClientDuplicatesAutoResolution.DUPLICATE_STATUS_NOT_SEARCHED : 1, ClientDuplicatesAutoResolution.DUPLICATE_STATUS_MATCHES_SEARCH_FAILED_TEST : 1 } )
        
        denied_pairs_with_info = self._read( 'duplicates_auto_resolution_denied_pairs', rule_1_read )
        
        self.assertEqual( denied_pairs_with_info, [] )
        
    
