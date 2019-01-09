from . import ClientConstants as CC
from . import ClientImportFileSeeds
from . import ClientImportOptions
from . import ClientTags
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
import os
import unittest
from mock import patch

class TestCheckerOptions( unittest.TestCase ):
    
    def test_checker_options( self ):
        
        regular_checker_options = ClientImportOptions.CheckerOptions( intended_files_per_check = 5, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        fast_checker_options = ClientImportOptions.CheckerOptions( intended_files_per_check = 2, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        slow_checker_options = ClientImportOptions.CheckerOptions( intended_files_per_check = 10, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        callous_checker_options = ClientImportOptions.CheckerOptions( intended_files_per_check = 5, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 60 ) )
        
        empty_file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        last_check_time = 10000000
        
        one_day_before = last_check_time - 86400
        
        for i in range( 50 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).hex()
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = one_day_before - 10
            
            file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
        
        for i in range( 50 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).hex()
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = last_check_time - 600
            
            file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
        
        bare_file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        url = 'https://wew.lad/' + 'early'
        
        file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
        
        file_seed.source_time = one_day_before - 10
        
        bare_file_seed_cache.AddFileSeeds( ( file_seed, ) )
        
        url = 'https://wew.lad/' + 'in_time_delta'
        
        file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
        
        file_seed.source_time = one_day_before + 10
        
        bare_file_seed_cache.AddFileSeeds( ( file_seed, ) )
        
        busy_file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        url = 'https://wew.lad/' + 'early'
        
        file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
        
        file_seed.source_time = one_day_before - 10
        
        busy_file_seed_cache.AddFileSeeds( ( file_seed, ) )
        
        for i in range( 8640 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).hex()
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = one_day_before + ( ( i + 1 ) * 10 ) - 1
            
            busy_file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
        
        new_thread_file_seed_cache = ClientImportFileSeeds.FileSeedCache()
        
        for i in range( 10 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).hex()
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = last_check_time - 600
            
            new_thread_file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
        
        # empty
        # should say ok if last_check_time is 0, so it can initialise
        # otherwise sperg out safely
        
        self.assertFalse( regular_checker_options.IsDead( empty_file_seed_cache, 0 ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( empty_file_seed_cache, 0 ), 'no files yet' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( empty_file_seed_cache, 0, 0 ), 0 )
        
        self.assertTrue( regular_checker_options.IsDead( empty_file_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( empty_file_seed_cache, last_check_time ), 'no files, unable to determine velocity' )
        
        # regular
        # current velocity should be 50 files per day for the day ones and 0 files per min for the callous minute one
        
        self.assertFalse( regular_checker_options.IsDead( file_seed_cache, last_check_time ) )
        self.assertFalse( fast_checker_options.IsDead( file_seed_cache, last_check_time ) )
        self.assertFalse( slow_checker_options.IsDead( file_seed_cache, last_check_time ) )
        self.assertTrue( callous_checker_options.IsDead( file_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( file_seed_cache, last_check_time ), 'at last check, found 50 files in previous 1 day' )
        self.assertEqual( fast_checker_options.GetPrettyCurrentVelocity( file_seed_cache, last_check_time ), 'at last check, found 50 files in previous 1 day' )
        self.assertEqual( slow_checker_options.GetPrettyCurrentVelocity( file_seed_cache, last_check_time ), 'at last check, found 50 files in previous 1 day' )
        self.assertEqual( callous_checker_options.GetPrettyCurrentVelocity( file_seed_cache, last_check_time ), 'at last check, found 0 files in previous 1 minute' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( file_seed_cache, last_check_time, 0 ), last_check_time + 8640 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( file_seed_cache, last_check_time, 0 ), last_check_time + 3456 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( file_seed_cache, last_check_time, 0 ), last_check_time + 17280 )
        
        # bare
        # 1 files per day
        
        self.assertFalse( regular_checker_options.IsDead( bare_file_seed_cache, last_check_time ) )
        self.assertTrue( callous_checker_options.IsDead( bare_file_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( bare_file_seed_cache, last_check_time ), 'at last check, found 1 files in previous 1 day' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( bare_file_seed_cache, last_check_time, 0 ), last_check_time + 86400 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( bare_file_seed_cache, last_check_time, 0 ), last_check_time + 86400 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( bare_file_seed_cache, last_check_time, 0 ), last_check_time + 86400 )
        
        # busy
        # 8640 files per day, 6 files per minute
        
        self.assertFalse( regular_checker_options.IsDead( busy_file_seed_cache, last_check_time ) )
        self.assertFalse( fast_checker_options.IsDead( busy_file_seed_cache, last_check_time ) )
        self.assertFalse( slow_checker_options.IsDead( busy_file_seed_cache, last_check_time ) )
        self.assertFalse( callous_checker_options.IsDead( busy_file_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( busy_file_seed_cache, last_check_time ), 'at last check, found 8,640 files in previous 1 day' )
        self.assertEqual( callous_checker_options.GetPrettyCurrentVelocity( busy_file_seed_cache, last_check_time ), 'at last check, found 6 files in previous 1 minute' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( busy_file_seed_cache, last_check_time, 0 ), last_check_time + 50 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( busy_file_seed_cache, last_check_time, 0 ), last_check_time + 30 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( busy_file_seed_cache, last_check_time, 0 ), last_check_time + 100 )
        self.assertEqual( callous_checker_options.GetNextCheckTime( busy_file_seed_cache, last_check_time, 0 ), last_check_time + 50 )
        
        # new thread
        # only had files from ten mins ago, so timings are different
        
        self.assertFalse( regular_checker_options.IsDead( new_thread_file_seed_cache, last_check_time ) )
        self.assertFalse( fast_checker_options.IsDead( new_thread_file_seed_cache, last_check_time ) )
        self.assertFalse( slow_checker_options.IsDead( new_thread_file_seed_cache, last_check_time ) )
        self.assertTrue( callous_checker_options.IsDead( new_thread_file_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( new_thread_file_seed_cache, last_check_time ), 'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( fast_checker_options.GetPrettyCurrentVelocity( new_thread_file_seed_cache, last_check_time ), 'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( slow_checker_options.GetPrettyCurrentVelocity( new_thread_file_seed_cache, last_check_time ), 'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( callous_checker_options.GetPrettyCurrentVelocity( new_thread_file_seed_cache, last_check_time ), 'at last check, found 0 files in previous 1 minute' )
        
        # these would be 360, 120, 600, but the 'don't check faster the time since last file post' bumps this up
        self.assertEqual( regular_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time, 0 ), last_check_time + 600 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time, 0 ), last_check_time + 600 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time, 0 ), last_check_time + 600 )
        
        # Let's test these new static timings, where if faster_than == slower_than, we just add that period to the 'last_next_check_time' (e.g. checking every sunday night)
        
        static_checker_options = ClientImportOptions.CheckerOptions( intended_files_per_check = 5, never_faster_than = 3600, never_slower_than = 3600, death_file_velocity = ( 1, 3600 ) )
        
        self.assertTrue( static_checker_options.IsDead( bare_file_seed_cache, last_check_time ) )
        
        last_next_check_time = last_check_time - 200
        
        with patch.object( HydrusData, 'GetNow', return_value = last_check_time + 10 ):
            
            self.assertEqual( static_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time, last_next_check_time ), last_next_check_time + 3600 )
            
        
    
class TestFileImportOptions( unittest.TestCase ):
    
    def test_file_import_options( self ):
        
        file_import_options = ClientImportOptions.FileImportOptions()
        
        exclude_deleted = False
        do_not_check_known_urls_before_importing = False
        do_not_check_hashes_before_importing = False
        allow_decompression_bombs = False
        min_size = None
        max_size = None
        max_gif_size = None
        min_resolution = None
        max_resolution = None
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        
        automatic_archive = False
        associate_source_urls = False
        
        file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
        
        present_new_files = True
        present_already_in_inbox_files = True
        present_already_in_archive_files = True
        
        file_import_options.SetPresentationOptions( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
        
        #
        
        self.assertFalse( file_import_options.ExcludesDeleted() )
        self.assertFalse( file_import_options.AllowsDecompressionBombs() )
        self.assertFalse( file_import_options.AutomaticallyArchives() )
        self.assertFalse( file_import_options.ShouldAssociateSourceURLs() )
        
        file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 480 )
        file_import_options.CheckFileIsValid( 65536, HC.APPLICATION_7Z, None, None )
        
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_AND_NEW, False ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_AND_NEW, True ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, False ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, True ) )
        
        self.assertFalse( file_import_options.ShouldPresent( CC.STATUS_DELETED, False ) )
        
        #
        
        exclude_deleted = True
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        
        self.assertTrue( file_import_options.ExcludesDeleted() )
        self.assertFalse( file_import_options.AllowsDecompressionBombs() )
        self.assertFalse( file_import_options.AutomaticallyArchives() )
        
        #
        
        allow_decompression_bombs = True
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        
        self.assertTrue( file_import_options.ExcludesDeleted() )
        self.assertTrue( file_import_options.AllowsDecompressionBombs() )
        self.assertFalse( file_import_options.AutomaticallyArchives() )
        
        #
        
        automatic_archive = True
        associate_source_urls  = True
        
        file_import_options.SetPostImportOptions( automatic_archive, associate_source_urls )
        
        self.assertTrue( file_import_options.ExcludesDeleted() )
        self.assertTrue( file_import_options.AllowsDecompressionBombs() )
        self.assertTrue( file_import_options.AutomaticallyArchives() )
        self.assertTrue( file_import_options.ShouldAssociateSourceURLs() )
        
        #
        
        min_size = 4096
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        
        file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.SizeException ):
            
            file_import_options.CheckFileIsValid( 512, HC.IMAGE_JPEG, 640, 480 )
            
        
        #
        
        min_size = None
        max_size = 2000
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        
        file_import_options.CheckFileIsValid( 1800, HC.IMAGE_JPEG, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.SizeException ):
            
            file_import_options.CheckFileIsValid( 2200, HC.IMAGE_JPEG, 640, 480 )
            
        
        #
        
        max_size = None
        max_gif_size = 2000
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        
        file_import_options.CheckFileIsValid( 1800, HC.IMAGE_JPEG, 640, 480 )
        file_import_options.CheckFileIsValid( 2200, HC.IMAGE_JPEG, 640, 480 )
        
        file_import_options.CheckFileIsValid( 1800, HC.IMAGE_GIF, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.SizeException ):
            
            file_import_options.CheckFileIsValid( 2200, HC.IMAGE_GIF, 640, 480 )
            
        
        #
        
        max_gif_size = None
        min_resolution = ( 200, 100 )
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        
        file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.SizeException ):
            
            file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 180, 480 )
            
        
        with self.assertRaises( HydrusExceptions.SizeException ):
            
            file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 80 )
            
        
        file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 180 )
        
        #
        
        min_resolution = None
        max_resolution = ( 3000, 4000 )
        
        file_import_options.SetPreImportOptions( exclude_deleted, do_not_check_known_urls_before_importing, do_not_check_hashes_before_importing, allow_decompression_bombs, min_size, max_size, max_gif_size, min_resolution, max_resolution )
        
        file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.SizeException ):
            
            file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 3200, 480 )
            
        
        with self.assertRaises( HydrusExceptions.SizeException ):
            
            file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 4200 )
            
        
        file_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 2800, 3800 )
        
        #
        
        present_new_files = False
        
        file_import_options.SetPresentationOptions( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
        
        self.assertFalse( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_AND_NEW, False ) )
        self.assertFalse( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_AND_NEW, True ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, False ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, True ) )
        
        #
        
        present_new_files = True
        present_already_in_inbox_files = False
        
        file_import_options.SetPresentationOptions( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
        
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_AND_NEW, False ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_AND_NEW, True ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, False ) )
        self.assertFalse( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, True ) )
        
        #
        
        present_already_in_inbox_files = True
        present_already_in_archive_files = False
        
        file_import_options.SetPresentationOptions( present_new_files, present_already_in_inbox_files, present_already_in_archive_files )
        
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_AND_NEW, False ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_AND_NEW, True ) )
        self.assertFalse( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, False ) )
        self.assertTrue( file_import_options.ShouldPresent( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, True ) )
        
    
class TestTagImportOptions( unittest.TestCase ):
    
    def test_basics( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        
        #
        
        default_tag_import_options = ClientImportOptions.TagImportOptions()
        
        self.assertEqual( default_tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB(), False )
        self.assertEqual( default_tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB(), False )
        
        blacklist = default_tag_import_options.GetTagBlacklist()
        
        self.assertEqual( blacklist.Filter( some_tags ), some_tags )
        
        self.assertEqual( default_tag_import_options.GetServiceKeysToContentUpdates( CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), {} )
        
        #
        
        tag_import_options = ClientImportOptions.TagImportOptions( fetch_tags_even_if_url_recognised_and_file_already_in_db = True )
        
        self.assertEqual( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB(), True )
        self.assertEqual( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB(), False )
        
        #
        
        tag_import_options = ClientImportOptions.TagImportOptions( fetch_tags_even_if_hash_recognised_and_file_already_in_db = True )
        
        self.assertEqual( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB(), False )
        self.assertEqual( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB(), True )
        
    
    def test_filter( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        #
        
        tag_blacklist = ClientTags.TagFilter()
        
        tag_blacklist.SetRule( 'series:', CC.FILTER_BLACKLIST )
        
        service_keys_to_service_tag_import_options = { example_service_key : ClientImportOptions.ServiceTagImportOptions( get_tags = True ) }
        
        tag_import_options = ClientImportOptions.TagImportOptions( tag_blacklist = tag_blacklist, service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetServiceKeysToContentUpdates( CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags )
        
        self.assertIn( example_service_key, result )
        
        self.assertEqual( len( result ), 1 )
        
        content_updates = result[ example_service_key ]
        
        filtered_tags = { 'bodysuit', 'character:samus aran' }
        
        self.assertTrue( len( content_updates ), len( filtered_tags ) )
        
    
    def test_services( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key_1 = HydrusData.GenerateKey()
        example_service_key_2 = HydrusData.GenerateKey()
        
        #
        
        service_keys_to_service_tag_import_options = {}
        
        service_keys_to_service_tag_import_options[ example_service_key_1 ] = ClientImportOptions.ServiceTagImportOptions( get_tags = True )
        service_keys_to_service_tag_import_options[ example_service_key_2 ] = ClientImportOptions.ServiceTagImportOptions( get_tags = False )
        
        tag_import_options = ClientImportOptions.TagImportOptions( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetServiceKeysToContentUpdates( CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags )
        
        self.assertIn( example_service_key_1, result )
        self.assertNotIn( example_service_key_2, result )
        
        self.assertTrue( len( result ), 2 )
        
        content_updates_1 = result[ example_service_key_1 ]
        
        self.assertEqual( len( content_updates_1 ), 3 )
        

class TestServiceTagImportOptions( unittest.TestCase ):
    
    def test_basics( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        #
        
        default_service_tag_import_options = ClientImportOptions.ServiceTagImportOptions()
        
        self.assertEqual( default_service_tag_import_options._get_tags, False )
        self.assertEqual( default_service_tag_import_options._additional_tags, [] )
        self.assertEqual( default_service_tag_import_options._to_new_files, True )
        self.assertEqual( default_service_tag_import_options._to_already_in_inbox, True )
        self.assertEqual( default_service_tag_import_options._to_already_in_archive, True )
        self.assertEqual( default_service_tag_import_options._only_add_existing_tags, False )
        
        self.assertEqual( default_service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), set() )
        
    
    def test_get_tags_filtering( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        #
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), some_tags )
        
        #
        
        only_namespaced = ClientTags.TagFilter()
        
        only_namespaced.SetRule( '', CC.FILTER_BLACKLIST )
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True, get_tags_filter = only_namespaced )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), { 'character:samus aran', 'series:metroid' } )
        
        #
        
        only_samus = ClientTags.TagFilter()
        
        only_samus.SetRule( '', CC.FILTER_BLACKLIST )
        only_samus.SetRule( ':', CC.FILTER_BLACKLIST )
        only_samus.SetRule( 'character:samus aran', CC.FILTER_WHITELIST )
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True, get_tags_filter = only_samus )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), { 'character:samus aran' } )
        
    
    def test_additional( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        #
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True, additional_tags = [ 'wew' ] )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), some_tags.union( [ 'wew' ] ) )
        
    
    def test_application( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        #
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True, to_new_files = True, to_already_in_inbox = False, to_already_in_archive = False )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), some_tags )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, True, example_hash, some_tags ), set() )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, False, example_hash, some_tags ), set() )
        
        #
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True, to_new_files = False, to_already_in_inbox = True, to_already_in_archive = False )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), set() )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, True, example_hash, some_tags ), some_tags )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, False, example_hash, some_tags ), set() )
        
        #
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True, to_new_files = False, to_already_in_inbox = False, to_already_in_archive = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), set() )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, True, example_hash, some_tags ), set() )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, False, example_hash, some_tags ), some_tags )
        
    
    def test_existing( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        existing_tags = { 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        #
        
        HG.test_controller.SetRead( 'filter_existing_tags', existing_tags )
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True, only_add_existing_tags = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), existing_tags )
        
        #
        
        some_tags = { 'explicit', 'bodysuit', 'character:samus aran', 'series:metroid' }
        existing_tags = { 'bodysuit' }
        
        only_unnamespaced = ClientTags.TagFilter()
        
        only_unnamespaced.SetRule( ':', CC.FILTER_BLACKLIST )
        
        HG.test_controller.SetRead( 'filter_existing_tags', existing_tags )
        
        service_tag_import_options = ClientImportOptions.ServiceTagImportOptions( get_tags = True, only_add_existing_tags = True, only_add_existing_tags_filter = only_unnamespaced )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, True, example_hash, some_tags ), { 'bodysuit', 'character:samus aran', 'series:metroid' } )
        
    
