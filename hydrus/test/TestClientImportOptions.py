import collections
import collections.abc
import os
import random
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusTags
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientLocation
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.importing.options import FileFilteringImportOptions
from hydrus.client.importing.options import LocationImportOptions
from hydrus.client.importing.options import NoteImportOptions
from hydrus.client.importing.options import PrefetchImportOptions
from hydrus.client.importing.options import PresentationImportOptions
from hydrus.client.importing.options import TagImportOptionsLegacy
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates

from hydrus.test import HelperFunctions as HF
from hydrus.test import TestGlobals as TG

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
        
        time_since_last_post = 600
        
        for i in range( 10 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).hex()
            
            file_seed = ClientImportFileSeeds.FileSeed( ClientImportFileSeeds.FILE_SEED_TYPE_URL, url )
            
            file_seed.source_time = last_check_time - time_since_last_post
            
            new_thread_file_seed_cache.AddFileSeeds( ( file_seed, ) )
            
        
        # empty
        # should say ok if last_check_time is 0, so it can initialise
        # otherwise sperg out safely
        
        self.assertFalse( regular_checker_options.IsDead( empty_file_seed_cache, 0 ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( empty_file_seed_cache, 0 ), 'no files yet' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( empty_file_seed_cache, 0 ), 0 )
        
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
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( file_seed_cache, last_check_time ), last_check_time + 8640 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( file_seed_cache, last_check_time ), last_check_time + 3456 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( file_seed_cache, last_check_time ), last_check_time + 17280 )
        
        # bare
        # 1 files per day
        
        self.assertFalse( regular_checker_options.IsDead( bare_file_seed_cache, last_check_time ) )
        self.assertTrue( callous_checker_options.IsDead( bare_file_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( bare_file_seed_cache, last_check_time ), 'at last check, found 1 files in previous 1 day' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( bare_file_seed_cache, last_check_time ), last_check_time + 86400 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( bare_file_seed_cache, last_check_time ), last_check_time + 86400 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( bare_file_seed_cache, last_check_time ), last_check_time + 86400 )
        
        # busy
        # 8640 files per day, 6 files per minute
        
        self.assertFalse( regular_checker_options.IsDead( busy_file_seed_cache, last_check_time ) )
        self.assertFalse( fast_checker_options.IsDead( busy_file_seed_cache, last_check_time ) )
        self.assertFalse( slow_checker_options.IsDead( busy_file_seed_cache, last_check_time ) )
        self.assertFalse( callous_checker_options.IsDead( busy_file_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( busy_file_seed_cache, last_check_time ), 'at last check, found 8,640 files in previous 1 day' )
        self.assertEqual( callous_checker_options.GetPrettyCurrentVelocity( busy_file_seed_cache, last_check_time ), 'at last check, found 6 files in previous 1 minute' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( busy_file_seed_cache, last_check_time ), last_check_time + 50 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( busy_file_seed_cache, last_check_time ), last_check_time + 30 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( busy_file_seed_cache, last_check_time ), last_check_time + 100 )
        self.assertEqual( callous_checker_options.GetNextCheckTime( busy_file_seed_cache, last_check_time ), last_check_time + 50 )
        
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
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time ), last_check_time + 300 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time ), last_check_time + 150 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time ), last_check_time + 600 )
        
        # Let's test the static timings, where if faster_than == slower_than
        
        static_checker_options = ClientImportOptions.CheckerOptions( intended_files_per_check = 5, never_faster_than = 3600, never_slower_than = 3600, death_file_velocity = ( 1, 3600 ) )
        
        self.assertTrue( static_checker_options.IsDead( bare_file_seed_cache, last_check_time ) )
        
        # normal situation
        last_check_time = HydrusTime.GetNow() - 5
        
        self.assertEqual( static_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time ), last_check_time + 3600 )
        
        # after a long pause
        last_check_time = HydrusTime.GetNow() - 100000
        
        self.assertEqual( static_checker_options.GetNextCheckTime( new_thread_file_seed_cache, last_check_time ), last_check_time + 3600 * ( 100000 // 3600 ) )
        
    

class TestFileFilteringImportOptions( unittest.TestCase ):
    
    def test_file_filtering_import_options( self ):
        
        exclude_deleted = False
        allow_decompression_bombs = False
        
        file_filtering_import_options = FileFilteringImportOptions.FileFilteringImportOptions()
        
        file_filtering_import_options.SetAllowsDecompressionBombs( allow_decompression_bombs )
        file_filtering_import_options.SetExcludesDeleted( exclude_deleted )
        
        #
        
        self.assertFalse( file_filtering_import_options.ExcludesDeleted() )
        self.assertFalse( file_filtering_import_options.AllowsDecompressionBombs() )
        
        file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 480 )
        file_filtering_import_options.CheckFileIsValid( 65536, HC.APPLICATION_7Z, None, None )
        
        #
        
        exclude_deleted = True
        
        file_filtering_import_options.SetExcludesDeleted( exclude_deleted )
        
        self.assertTrue( file_filtering_import_options.ExcludesDeleted() )
        
        #
        
        allow_decompression_bombs = True
        
        file_filtering_import_options.SetAllowsDecompressionBombs( allow_decompression_bombs )
        
        self.assertTrue( file_filtering_import_options.ExcludesDeleted() )
        self.assertTrue( file_filtering_import_options.AllowsDecompressionBombs() )
        
        #
        
        min_size = 4096
        
        file_filtering_import_options.SetMinSize( min_size )
        
        file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.FileImportRulesException ):
            
            file_filtering_import_options.CheckFileIsValid( 512, HC.IMAGE_JPEG, 640, 480 )
            
        
        #
        
        min_size = None
        max_size = 2000
        
        file_filtering_import_options.SetMinSize( min_size )
        file_filtering_import_options.SetMaxSize( max_size )
        
        file_filtering_import_options.CheckFileIsValid( 1800, HC.IMAGE_JPEG, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.FileImportRulesException ):
            
            file_filtering_import_options.CheckFileIsValid( 2200, HC.IMAGE_JPEG, 640, 480 )
            
        
        #
        
        max_size = None
        max_gif_size = 2000
        
        file_filtering_import_options.SetMaxSize( max_size )
        file_filtering_import_options.SetMaxGifSize( max_gif_size )
        
        file_filtering_import_options.CheckFileIsValid( 1800, HC.IMAGE_JPEG, 640, 480 )
        file_filtering_import_options.CheckFileIsValid( 2200, HC.IMAGE_JPEG, 640, 480 )
        
        file_filtering_import_options.CheckFileIsValid( 1800, HC.ANIMATION_GIF, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.FileImportRulesException ):
            
            file_filtering_import_options.CheckFileIsValid( 2200, HC.ANIMATION_GIF, 640, 480 )
            
        
        #
        
        max_gif_size = None
        min_resolution = ( 200, 100 )
        
        file_filtering_import_options.SetMaxGifSize( max_gif_size )
        file_filtering_import_options.SetMinResolution( min_resolution )
        
        file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.FileImportRulesException ):
            
            file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 180, 480 )
            
        
        with self.assertRaises( HydrusExceptions.FileImportRulesException ):
            
            file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 80 )
            
        
        file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 180 )
        
        #
        
        min_resolution = None
        max_resolution = ( 3000, 4000 )
        
        file_filtering_import_options.SetMinResolution( min_resolution )
        file_filtering_import_options.SetMaxResolution( max_resolution )
        
        file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 480 )
        
        with self.assertRaises( HydrusExceptions.FileImportRulesException ):
            
            file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 3200, 480 )
            
        
        with self.assertRaises( HydrusExceptions.FileImportRulesException ):
            
            file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 640, 4200 )
            
        
        file_filtering_import_options.CheckFileIsValid( 65536, HC.IMAGE_JPEG, 2800, 3800 )
        
    

def GetNotesMediaResult( hash, names_to_notes ):
    
    file_id = 123
    size = random.randint( 8192, 20 * 1048576 )
    mime = random.choice( [ HC.IMAGE_JPEG, HC.VIDEO_WEBM, HC.APPLICATION_PDF ] )
    width = random.randint( 200, 4096 )
    height = random.randint( 200, 4096 )
    duration_ms = random.choice( [ 220, 16.66667, None ] )
    has_audio = random.choice( [ True, False ] )
    
    file_info_manager = ClientMediaManagers.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration_ms = duration_ms, has_audio = has_audio )
    
    service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
    service_keys_to_statuses_to_display_tags = collections.defaultdict( HydrusData.default_dict_set )
    
    tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
    
    times_manager = ClientMediaManagers.TimesManager()
    
    locations_manager = ClientMediaManagers.LocationsManager( set(), set(), set(), set(), times_manager, inbox = True )
    ratings_manager = ClientMediaManagers.RatingsManager( {} )
    notes_manager = ClientMediaManagers.NotesManager( names_to_notes )
    file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager( times_manager )
    
    media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
    
    return media_result
    

class TestLocationImportOptions( unittest.TestCase ):
    
    def test_location_import_options( self ):
        
        destination_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY )
        automatic_archive = False
        do_archive_already_in_db_files = False
        do_import_destinations_on_already_in_db_files = False
        associate_primary_urls = False
        associate_source_urls = False
        
        location_import_options = LocationImportOptions.LocationImportOptions()
        
        location_import_options.SetDestinationLocationContext( destination_location_context )
        location_import_options.SetAutomaticallyArchives( automatic_archive )
        location_import_options.SetDoAutomaticArchiveOnAlreadyInDBFiles( do_archive_already_in_db_files )
        location_import_options.SetDoImportDestinationsOnAlreadyInDBFiles( do_import_destinations_on_already_in_db_files )
        location_import_options.SetShouldAssociatePrimaryURLs( associate_primary_urls )
        location_import_options.SetShouldAssociateSourceURLs( associate_source_urls )
        
        #
        
        self.assertEqual( location_import_options.GetDestinationLocationContext(), destination_location_context )
        self.assertEqual( location_import_options.AutomaticallyArchives(), automatic_archive )
        self.assertEqual( location_import_options.DoAutomaticArchiveOnAlreadyInDBFiles(), do_archive_already_in_db_files )
        self.assertEqual( location_import_options.DoImportDestinationsOnAlreadyInDBFiles(), do_import_destinations_on_already_in_db_files )
        self.assertEqual( location_import_options.ShouldAssociatePrimaryURLs(), associate_primary_urls )
        self.assertEqual( location_import_options.ShouldAssociateSourceURLs(), associate_source_urls )
        
        #
        
        automatic_archive = True
        
        location_import_options.SetAutomaticallyArchives( automatic_archive )
        
        #
        
        self.assertEqual( location_import_options.GetDestinationLocationContext(), destination_location_context )
        self.assertEqual( location_import_options.AutomaticallyArchives(), automatic_archive )
        self.assertEqual( location_import_options.DoAutomaticArchiveOnAlreadyInDBFiles(), do_archive_already_in_db_files )
        self.assertEqual( location_import_options.DoImportDestinationsOnAlreadyInDBFiles(), do_import_destinations_on_already_in_db_files )
        self.assertEqual( location_import_options.ShouldAssociatePrimaryURLs(), associate_primary_urls )
        self.assertEqual( location_import_options.ShouldAssociateSourceURLs(), associate_source_urls )
        
        #
        
        do_archive_already_in_db_files = True
        
        location_import_options.SetDoAutomaticArchiveOnAlreadyInDBFiles( do_archive_already_in_db_files )
        
        #
        
        self.assertEqual( location_import_options.GetDestinationLocationContext(), destination_location_context )
        self.assertEqual( location_import_options.AutomaticallyArchives(), automatic_archive )
        self.assertEqual( location_import_options.DoAutomaticArchiveOnAlreadyInDBFiles(), do_archive_already_in_db_files )
        self.assertEqual( location_import_options.DoImportDestinationsOnAlreadyInDBFiles(), do_import_destinations_on_already_in_db_files )
        self.assertEqual( location_import_options.ShouldAssociatePrimaryURLs(), associate_primary_urls )
        self.assertEqual( location_import_options.ShouldAssociateSourceURLs(), associate_source_urls )
        
        #
        
        do_import_destinations_on_already_in_db_files = True
        
        location_import_options.SetDoImportDestinationsOnAlreadyInDBFiles( do_import_destinations_on_already_in_db_files )
        
        #
        
        self.assertEqual( location_import_options.GetDestinationLocationContext(), destination_location_context )
        self.assertEqual( location_import_options.AutomaticallyArchives(), automatic_archive )
        self.assertEqual( location_import_options.DoAutomaticArchiveOnAlreadyInDBFiles(), do_archive_already_in_db_files )
        self.assertEqual( location_import_options.DoImportDestinationsOnAlreadyInDBFiles(), do_import_destinations_on_already_in_db_files )
        self.assertEqual( location_import_options.ShouldAssociatePrimaryURLs(), associate_primary_urls )
        self.assertEqual( location_import_options.ShouldAssociateSourceURLs(), associate_source_urls )
        
        #
        
        associate_primary_urls = True
        
        location_import_options.SetShouldAssociatePrimaryURLs( associate_primary_urls )
        
        #
        
        self.assertEqual( location_import_options.GetDestinationLocationContext(), destination_location_context )
        self.assertEqual( location_import_options.AutomaticallyArchives(), automatic_archive )
        self.assertEqual( location_import_options.DoAutomaticArchiveOnAlreadyInDBFiles(), do_archive_already_in_db_files )
        self.assertEqual( location_import_options.DoImportDestinationsOnAlreadyInDBFiles(), do_import_destinations_on_already_in_db_files )
        self.assertEqual( location_import_options.ShouldAssociatePrimaryURLs(), associate_primary_urls )
        self.assertEqual( location_import_options.ShouldAssociateSourceURLs(), associate_source_urls )
        
        #
        
        associate_source_urls = True
        
        location_import_options.SetShouldAssociateSourceURLs( associate_source_urls )
        
        #
        
        self.assertEqual( location_import_options.GetDestinationLocationContext(), destination_location_context )
        self.assertEqual( location_import_options.AutomaticallyArchives(), automatic_archive )
        self.assertEqual( location_import_options.DoAutomaticArchiveOnAlreadyInDBFiles(), do_archive_already_in_db_files )
        self.assertEqual( location_import_options.DoImportDestinationsOnAlreadyInDBFiles(), do_import_destinations_on_already_in_db_files )
        self.assertEqual( location_import_options.ShouldAssociatePrimaryURLs(), associate_primary_urls )
        self.assertEqual( location_import_options.ShouldAssociateSourceURLs(), associate_source_urls )
        
        #
        
        destination_location_context = ClientLocation.LocationContext( current_service_keys = set(), deleted_service_keys = set() )
        
        location_import_options.SetDestinationLocationContext( destination_location_context )
        
        with self.assertRaises( HydrusExceptions.FileImportBlockException ):
            
            location_import_options.CheckReadyToImport()
            
        
    

class TestNoteImportOptions( unittest.TestCase ):
    
    def test_basics( self ):
        
        example_hash = HydrusData.GenerateKey()
        existing_names_to_notes = { 'notes' : 'here is a note' }
        
        media_result = GetNotesMediaResult( example_hash, existing_names_to_notes )
        
        #
        
        note_import_options = NoteImportOptions.NoteImportOptions()
        
        note_import_options.SetGetNotes( True )
        note_import_options.SetExtendExistingNoteIfPossible( True )
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_IGNORE )
        
        HF.compare_content_update_packages( self, note_import_options.GetContentUpdatePackage( media_result, [] ), ClientContentUpdates.ContentUpdatePackage() )
        
        #
        
        names_and_notes = [ ( 'test', 'yes' ) ]
        
        result = note_import_options.GetContentUpdatePackage( media_result, names_and_notes )
        expected_result = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_NOTES_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'test', 'yes' ) ) )
        
        HF.compare_content_update_packages( self, result, expected_result )
        
        note_import_options.SetGetNotes( False )
        
        result = note_import_options.GetContentUpdatePackage( media_result, names_and_notes )
        
        HF.compare_content_update_packages( self, result, ClientContentUpdates.ContentUpdatePackage() )
        
        note_import_options.SetGetNotes( True )
        
        #
        
        names_and_notes = [ ( 'garbage', 'lol randumb' ), ( 'artist', 'I drew this in two days' ) ]
        
        note_import_options.SetNameWhitelist( [ 'artist' ] )
        
        result = note_import_options.GetContentUpdatePackage( media_result, names_and_notes )
        expected_result = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_NOTES_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'artist', 'I drew this in two days' ) ) )
        
        HF.compare_content_update_packages( self, result, expected_result )
        
        note_import_options.SetNameWhitelist( [] )
        
        #
        
        extending_names_and_notes = [ ( 'notes', 'and here is a note that is more interesting' ) ]
        
        note_import_options.SetExtendExistingNoteIfPossible( True )
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_IGNORE )
        
        result = note_import_options.GetContentUpdatePackage( media_result, extending_names_and_notes )
        expected_result = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_NOTES_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'notes', 'and here is a note that is more interesting' ) ) )
        
        HF.compare_content_update_packages( self, result, expected_result )
        
        note_import_options.SetExtendExistingNoteIfPossible( False )
        
        result = note_import_options.GetContentUpdatePackage( media_result, extending_names_and_notes )
        
        HF.compare_content_update_packages( self, result, ClientContentUpdates.ContentUpdatePackage() )
        
        #
        
        conflict_names_and_notes = [ ( 'notes', 'other note' ) ]
        
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_IGNORE )
        
        result = note_import_options.GetContentUpdatePackage( media_result, conflict_names_and_notes )
        
        HF.compare_content_update_packages( self, result, ClientContentUpdates.ContentUpdatePackage() )
        
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_REPLACE )
        
        result = note_import_options.GetContentUpdatePackage( media_result, conflict_names_and_notes )
        expected_result = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_NOTES_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'notes', 'other note' ) ) )
        
        HF.compare_content_update_packages( self, result, expected_result )
        
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME )
        
        result = note_import_options.GetContentUpdatePackage( media_result, conflict_names_and_notes )
        expected_result = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_NOTES_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'notes (1)', 'other note' ) ) )
        
        HF.compare_content_update_packages( self, result, expected_result )
        
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_APPEND )
        
        result = note_import_options.GetContentUpdatePackage( media_result, conflict_names_and_notes )
        expected_result = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.LOCAL_NOTES_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'notes', 'here is a note' + '\n' * 2 + 'other note' ) ) )
        
        HF.compare_content_update_packages( self, result, expected_result )
        
        #
        
        multinotes = [ ( 'notes', 'other note' ), ( 'b', 'bbb' ), ( 'c', 'ccc' ) ]
        
        note_import_options.SetConflictResolution( NoteImportOptions.NOTE_IMPORT_CONFLICT_IGNORE )
        
        result = note_import_options.GetContentUpdatePackage( media_result, multinotes )
        expected_result = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'b', 'bbb' ) ), ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'c', 'ccc' ) ) ] )
        
        HF.compare_content_update_packages( self, result, expected_result )
        
        #
        
        renames = [ ( 'a', 'aaa' ), ( 'wew', 'wew note' ) ]
        
        note_import_options.SetAllNameOverride( 'override' )
        note_import_options.SetNamesToNameOverrides( { 'wew' : 'lad' } )
        
        result = note_import_options.GetContentUpdatePackage( media_result, renames )
        expected_result = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'override', 'aaa' ) ), ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( example_hash, 'lad', 'wew note' ) ) ] )
        
        HF.compare_content_update_packages( self, result, expected_result )
        
    
def GetTagsMediaResult( hash, in_inbox, service_key, deleted_tags ):
    
    file_id = 123
    size = random.randint( 8192, 20 * 1048576 )
    mime = random.choice( [ HC.IMAGE_JPEG, HC.VIDEO_WEBM, HC.APPLICATION_PDF ] )
    width = random.randint( 200, 4096 )
    height = random.randint( 200, 4096 )
    duration_ms = random.choice( [ 220, 16.66667, None ] )
    has_audio = random.choice( [ True, False ] )
    
    file_info_manager = ClientMediaManagers.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration_ms = duration_ms, has_audio = has_audio )
    
    service_keys_to_statuses_to_tags = collections.defaultdict( HydrusData.default_dict_set )
    
    service_keys_to_statuses_to_tags[ service_key ] = { HC.CONTENT_STATUS_DELETED : deleted_tags }
    
    service_keys_to_statuses_to_display_tags = collections.defaultdict( HydrusData.default_dict_set )
    
    tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
    
    times_manager = ClientMediaManagers.TimesManager()
    
    locations_manager = ClientMediaManagers.LocationsManager( set(), set(), set(), set(), times_manager, inbox = in_inbox )
    ratings_manager = ClientMediaManagers.RatingsManager( {} )
    notes_manager = ClientMediaManagers.NotesManager( {} )
    file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager( times_manager )
    
    media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
    
    return media_result
    

class TestPrefetchImportOptions( unittest.TestCase ):
    
    def test_prefetch_import_options( self ):
        
        prefetch_import_options = PrefetchImportOptions.PrefetchImportOptions()
        
        prefetch_import_options.SetPreImportHashCheckType( PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE )
        prefetch_import_options.SetPreImportURLCheckType( PrefetchImportOptions.DO_CHECK )
        prefetch_import_options.SetPreImportURLCheckLooksForNeighbourSpam( True )
        
        self.assertEqual( prefetch_import_options.GetPreImportHashCheckType(), PrefetchImportOptions.DO_CHECK_AND_MATCHES_ARE_DISPOSITIVE )
        self.assertEqual( prefetch_import_options.GetPreImportURLCheckType(), PrefetchImportOptions.DO_CHECK )
        self.assertTrue( prefetch_import_options.PreImportURLCheckLooksForNeighbourSpam() )
        
    

class TestPresentationImportOptions( unittest.TestCase ):
    
    def test_presentation_import_options( self ):
        
        new_and_inboxed_hash = HydrusData.GenerateKey()
        new_and_archived_hash = HydrusData.GenerateKey()
        already_in_and_inboxed_hash = HydrusData.GenerateKey()
        already_in_and_archived_hash = HydrusData.GenerateKey()
        new_and_inboxed_but_trashed_hash = HydrusData.GenerateKey()
        skipped_hash = HydrusData.GenerateKey()
        deleted_hash = HydrusData.GenerateKey()
        failed_hash = HydrusData.GenerateKey()
        
        hashes_and_statuses = [
            ( new_and_inboxed_hash, CC.STATUS_SUCCESSFUL_AND_NEW ),
            ( new_and_archived_hash, CC.STATUS_SUCCESSFUL_AND_NEW ),
            ( already_in_and_inboxed_hash, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ),
            ( already_in_and_archived_hash, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT ),
            ( new_and_inboxed_but_trashed_hash, CC.STATUS_SUCCESSFUL_AND_NEW ),
            ( skipped_hash, CC.STATUS_SKIPPED ),
            ( deleted_hash, CC.STATUS_DELETED ),
            ( failed_hash, CC.STATUS_ERROR )
        ]
        
        # all good
        
        TG.test_controller.ClearReads( 'inbox_hashes' )
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_ANY_GOOD )
        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_AGNOSTIC )
        presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
        
        pre_filter_expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash,
            already_in_and_inboxed_hash,
            already_in_and_archived_hash,
            new_and_inboxed_but_trashed_hash
        ]
        
        expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash,
            already_in_and_inboxed_hash,
            already_in_and_archived_hash
        ]
        
        TG.test_controller.SetRead( 'inbox_hashes', 'not used' )
        TG.test_controller.SetRead( 'filter_hashes', expected_result )
        
        result = presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'filter_hashes' )
        
        self.assertEqual( args, ( ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, ) ), pre_filter_expected_result ) )
        
        self.assertEqual( result, expected_result )
        
        # all good and trash too
        
        TG.test_controller.ClearReads( 'inbox_hashes' )
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_ANY_GOOD )
        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_AGNOSTIC )
        presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY ) )
        
        pre_filter_expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash,
            already_in_and_inboxed_hash,
            already_in_and_archived_hash,
            new_and_inboxed_but_trashed_hash
        ]
        
        expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash,
            already_in_and_inboxed_hash,
            already_in_and_archived_hash,
            new_and_inboxed_but_trashed_hash
        ]
        
        TG.test_controller.SetRead( 'inbox_hashes', 'not used' )
        TG.test_controller.SetRead( 'filter_hashes', expected_result )
        
        result = presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'filter_hashes' )
        
        self.assertEqual( args, ( ClientLocation.LocationContext( current_service_keys = ( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, ) ), pre_filter_expected_result ) )
        
        self.assertEqual( result, expected_result )
        
        # silent
        
        TG.test_controller.ClearReads( 'inbox_hashes' )
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NONE )
        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_AGNOSTIC )
        presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
        
        expected_result = []
        
        TG.test_controller.SetRead( 'inbox_hashes', 'not used' )
        TG.test_controller.SetRead( 'filter_hashes', 'not used' )
        
        result = presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
        self.assertEqual( result, expected_result )
        
        # new files only
        
        TG.test_controller.ClearReads( 'inbox_hashes' )
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_AGNOSTIC )
        presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
        
        pre_filter_expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash,
            new_and_inboxed_but_trashed_hash
        ]
        
        expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash
        ]
        
        TG.test_controller.SetRead( 'inbox_hashes', 'not used' )
        TG.test_controller.SetRead( 'filter_hashes', expected_result )
        
        result = presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'filter_hashes' )
        
        self.assertEqual( args, ( ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, ) ), pre_filter_expected_result ) )
        
        self.assertEqual( result, expected_result )
        
        # inbox only
        
        TG.test_controller.ClearReads( 'inbox_hashes' )
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_ANY_GOOD )
        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_REQUIRE_INBOX )
        presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
        
        pre_inbox_filter_expected_result = {
            new_and_inboxed_hash,
            new_and_archived_hash,
            already_in_and_inboxed_hash,
            already_in_and_archived_hash,
            new_and_inboxed_but_trashed_hash
        }
        
        inbox_filter_answer = {
            new_and_inboxed_hash,
            already_in_and_inboxed_hash,
            new_and_inboxed_but_trashed_hash
        }
        
        pre_filter_expected_result = [
            new_and_inboxed_hash,
            already_in_and_inboxed_hash,
            new_and_inboxed_but_trashed_hash
        ]
        
        expected_result = [
            new_and_inboxed_hash,
            already_in_and_inboxed_hash
        ]
        
        TG.test_controller.SetRead( 'inbox_hashes', inbox_filter_answer )
        TG.test_controller.SetRead( 'filter_hashes', expected_result )
        
        result = presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'inbox_hashes' )
        
        self.assertEqual( args, ( pre_inbox_filter_expected_result, ) )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'filter_hashes' )
        
        self.assertEqual( args, ( ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, ) ), pre_filter_expected_result ) )
        
        self.assertEqual( result, expected_result )
        
        # new only
        
        TG.test_controller.ClearReads( 'inbox_hashes' )
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_AGNOSTIC )
        presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
        
        pre_filter_expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash,
            new_and_inboxed_but_trashed_hash
        ]
        
        expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash
        ]
        
        TG.test_controller.SetRead( 'inbox_hashes', 'not used' )
        TG.test_controller.SetRead( 'filter_hashes', expected_result )
        
        result = presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'filter_hashes' )
        
        self.assertEqual( args, ( ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, ) ), pre_filter_expected_result ) )
        
        self.assertEqual( result, expected_result )
        
        # new and inbox only
        
        TG.test_controller.ClearReads( 'inbox_hashes' )
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_REQUIRE_INBOX )
        presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
        
        pre_inbox_filter_expected_result = {
            new_and_inboxed_hash,
            new_and_archived_hash,
            new_and_inboxed_but_trashed_hash
        }
        
        inbox_filter_answer = {
            new_and_inboxed_hash,
            new_and_inboxed_but_trashed_hash
        }
        
        pre_filter_expected_result = [
            new_and_inboxed_hash,
            new_and_inboxed_but_trashed_hash
        ]
        
        expected_result = [
            new_and_inboxed_hash
        ]
        
        TG.test_controller.SetRead( 'inbox_hashes', inbox_filter_answer )
        TG.test_controller.SetRead( 'filter_hashes', expected_result )
        
        result = presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'inbox_hashes' )
        
        self.assertEqual( args, ( pre_inbox_filter_expected_result, ) )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'filter_hashes' )
        
        self.assertEqual( args, ( ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, ) ), pre_filter_expected_result ) )
        
        self.assertEqual( result, expected_result )
        
        # new or inbox only
        
        TG.test_controller.ClearReads( 'inbox_hashes' )
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        presentation_import_options = PresentationImportOptions.PresentationImportOptions()
        
        presentation_import_options.SetPresentationStatus( PresentationImportOptions.PRESENTATION_STATUS_NEW_ONLY )
        presentation_import_options.SetPresentationInbox( PresentationImportOptions.PRESENTATION_INBOX_AND_INCLUDE_ALL_INBOX )
        presentation_import_options.SetLocationContext( ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY ) )
        
        pre_inbox_filter_expected_result = {
            already_in_and_inboxed_hash,
            already_in_and_archived_hash
        }
        
        inbox_filter_answer = {
            already_in_and_inboxed_hash
        }
        
        pre_filter_expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash,
            already_in_and_inboxed_hash,
            new_and_inboxed_but_trashed_hash
        ]
        
        expected_result = [
            new_and_inboxed_hash,
            new_and_archived_hash,
            already_in_and_inboxed_hash,
        ]
        
        TG.test_controller.SetRead( 'inbox_hashes', inbox_filter_answer )
        TG.test_controller.SetRead( 'filter_hashes', expected_result )
        
        result = presentation_import_options.GetPresentedHashes( hashes_and_statuses )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'inbox_hashes' )
        
        self.assertEqual( args, ( pre_inbox_filter_expected_result, ) )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'filter_hashes' )
        
        self.assertEqual( args, ( ClientLocation.LocationContext( current_service_keys = ( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, ) ), pre_filter_expected_result ) )
        
        self.assertEqual( result, expected_result )
        
    
class TestTagImportOptions( unittest.TestCase ):
    
    def test_basics( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = TG.test_controller.example_tag_repo_service_key
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, set() )
        
        #
        
        default_tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy()
        
        self.assertEqual( default_tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB(), False )
        self.assertEqual( default_tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB(), False )
        
        blacklist = default_tag_import_options.GetTagBlacklist()
        
        self.assertEqual( blacklist.Filter( some_tags ), some_tags )
        
        whitelist = default_tag_import_options.GetTagWhitelist()
        
        self.assertEqual( whitelist, [] )
        
        HF.compare_content_update_packages( self, default_tag_import_options.GetContentUpdatePackage( CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), ClientContentUpdates.ContentUpdatePackage() )
        
        #
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( fetch_tags_even_if_url_recognised_and_file_already_in_db = True )
        
        self.assertEqual( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB(), True )
        self.assertEqual( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB(), False )
        
        #
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( fetch_tags_even_if_hash_recognised_and_file_already_in_db = True )
        
        self.assertEqual( tag_import_options.ShouldFetchTagsEvenIfURLKnownAndFileAlreadyInDB(), False )
        self.assertEqual( tag_import_options.ShouldFetchTagsEvenIfHashKnownAndFileAlreadyInDB(), True )
        
    
    def test_blacklist( self ):
        
        example_service_key = TG.test_controller.example_tag_repo_service_key
        
        tag_blacklist = HydrusTags.TagFilter()
        
        tag_blacklist.SetRule( 'series:', HC.FILTER_BLACKLIST )
        
        service_keys_to_service_tag_import_options = { example_service_key : TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True ) }
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( tag_blacklist = tag_blacklist, service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        with self.assertRaises( HydrusExceptions.VetoException ):
            
            tag_import_options.CheckTagsVeto( { 'bodysuit', 'series:metroid' }, set() )
            
        
        with self.assertRaises( HydrusExceptions.VetoException ):
            
            tag_import_options.CheckTagsVeto( { 'bodysuit' }, { 'series:metroid' } )
            
        
        tag_import_options.CheckTagsVeto( { 'bodysuit' }, set() )
        
    
    def test_whitelist( self ):
        
        example_service_key = TG.test_controller.example_tag_repo_service_key
        
        tag_whitelist = [ 'bodysuit' ]
        
        service_keys_to_service_tag_import_options = { example_service_key : TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True ) }
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( tag_whitelist = tag_whitelist, service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        with self.assertRaises( HydrusExceptions.VetoException ):
            
            tag_import_options.CheckTagsVeto( { 'series:metroid' }, set() )
            
        
        tag_import_options.CheckTagsVeto( { 'bodysuit', 'series:metroid' }, set() )
        tag_import_options.CheckTagsVeto( { 'series:metroid' }, { 'bodysuit' } )
        
    
    def test_external_tags( self ):
        
        some_tags = set()
        example_hash = HydrusData.GenerateKey()
        example_service_key = TG.test_controller.example_tag_repo_service_key
        
        external_filterable_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        external_additional_service_keys_to_tags = { example_service_key : { 'series:evangelion' } }
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, set() )
        
        #
        
        service_keys_to_service_tag_import_options = { example_service_key : TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True ) }
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetContentUpdatePackage( CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags, external_filterable_tags = external_filterable_tags, external_additional_service_keys_to_tags = external_additional_service_keys_to_tags )
        
        self.assertIn( example_service_key, dict( result.IterateContentUpdates() ) )
        
        self.assertEqual( len( dict( result.IterateContentUpdates() ) ), 1 )
        
        content_updates = dict( result.IterateContentUpdates() )[ example_service_key ]
        
        filtered_tags = { 'bodysuit', 'character:samus aran', 'series:metroid', 'series:evangelion' }
        result_tags = { c_u.GetRow()[0] for c_u in content_updates }
        
        self.assertEqual( result_tags, filtered_tags )
        
        #
        
        get_tags_filter = HydrusTags.TagFilter()
        
        get_tags_filter.SetRule( 'series:', HC.FILTER_BLACKLIST )
        
        service_keys_to_service_tag_import_options = { example_service_key : TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, get_tags_filter = get_tags_filter ) }
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetContentUpdatePackage( CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags, external_filterable_tags = external_filterable_tags, external_additional_service_keys_to_tags = external_additional_service_keys_to_tags )
        
        self.assertIn( example_service_key, dict( result.IterateContentUpdates() ) )
        
        self.assertEqual( len( dict( result.IterateContentUpdates() ) ), 1 )
        
        content_updates = dict( result.IterateContentUpdates() )[ example_service_key ]
        
        filtered_tags = { 'bodysuit', 'character:samus aran', 'series:evangelion' }
        result_tags = { c_u.GetRow()[0] for c_u in content_updates }
        
        self.assertEqual( result_tags, filtered_tags )
        
    
    def test_services( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key_1 = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
        example_service_key_2 = TG.test_controller.example_tag_repo_service_key
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key_1, set() )
        
        #
        
        service_keys_to_service_tag_import_options = {}
        
        service_keys_to_service_tag_import_options[ example_service_key_1 ] = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True )
        service_keys_to_service_tag_import_options[ example_service_key_2 ] = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = False )
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetContentUpdatePackage( CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags )
        
        self.assertIn( example_service_key_1, dict( result.IterateContentUpdates() ) )
        self.assertNotIn( example_service_key_2, dict( result.IterateContentUpdates() ) )
        
        self.assertTrue( len( dict( result.IterateContentUpdates() ) ) == 1 )
        
        content_updates_1 = dict( result.IterateContentUpdates() )[ example_service_key_1 ]
        
        filtered_tags = { 'bodysuit', 'character:samus aran', 'series:evangelion' }
        result_tags = { c_u.GetRow()[0] for c_u in content_updates_1 }
        
    
    def test_overwrite_deleted_filterable( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = TG.test_controller.example_tag_repo_service_key
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, { 'bodysuit', 'series:metroid' } )
        
        #
        
        service_keys_to_service_tag_import_options = { example_service_key : TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True ) }
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetContentUpdatePackage( CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags )
        
        self.assertIn( example_service_key, dict( result.IterateContentUpdates() ) )
        
        self.assertEqual( len( dict( result.IterateContentUpdates() ) ), 1 )
        
        content_updates = dict( result.IterateContentUpdates() )[ example_service_key ]
        
        filtered_tags = { 'character:samus aran' }
        result_tags = { c_u.GetRow()[0] for c_u in content_updates }
        
        self.assertEqual( result_tags, filtered_tags )
        
        #
        
        service_keys_to_service_tag_import_options = { example_service_key : TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, get_tags_overwrite_deleted = True ) }
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetContentUpdatePackage( CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags )
        
        self.assertIn( example_service_key, dict( result.IterateContentUpdates() ) )
        
        self.assertEqual( len( dict( result.IterateContentUpdates() ) ), 1 )
        
        content_updates = dict( result.IterateContentUpdates() )[ example_service_key ]
        
        filtered_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        result_tags = { c_u.GetRow()[0] for c_u in content_updates }
        
        self.assertEqual( result_tags, filtered_tags )
        
    
    def test_overwrite_deleted_additional( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = TG.test_controller.example_tag_repo_service_key
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, { 'bodysuit', 'series:metroid' } )
        
        #
        
        service_keys_to_service_tag_import_options = { example_service_key : TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, additional_tags = some_tags ) }
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetContentUpdatePackage( CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags )
        
        self.assertIn( example_service_key, dict( result.IterateContentUpdates() ) )
        
        self.assertEqual( len( dict( result.IterateContentUpdates() ) ), 1 )
        
        content_updates = dict( result.IterateContentUpdates() )[ example_service_key ]
        
        filtered_tags = { 'character:samus aran' }
        result_tags = { c_u.GetRow()[0] for c_u in content_updates }
        
        self.assertEqual( result_tags, filtered_tags )
        
        #
        
        service_keys_to_service_tag_import_options = { example_service_key : TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, get_tags_overwrite_deleted = True, additional_tags = some_tags ) }
        
        tag_import_options = TagImportOptionsLegacy.TagImportOptionsLegacy( service_keys_to_service_tag_import_options = service_keys_to_service_tag_import_options )
        
        result = tag_import_options.GetContentUpdatePackage( CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags )
        
        self.assertIn( example_service_key, dict( result.IterateContentUpdates() ) )
        
        self.assertEqual( len( dict( result.IterateContentUpdates() ) ), 1 )
        
        content_updates = dict( result.IterateContentUpdates() )[ example_service_key ]
        
        filtered_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        result_tags = { c_u.GetRow()[0] for c_u in content_updates }
        
        self.assertEqual( result_tags, filtered_tags )
        
    
class TestServiceTagImportOptions( unittest.TestCase ):
    
    def test_basics( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, set() )
        
        #
        
        default_service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions()
        
        self.assertEqual( default_service_tag_import_options._get_tags, False )
        self.assertEqual( default_service_tag_import_options._additional_tags, [] )
        self.assertEqual( default_service_tag_import_options._to_new_files, True )
        self.assertEqual( default_service_tag_import_options._to_already_in_inbox, True )
        self.assertEqual( default_service_tag_import_options._to_already_in_archive, True )
        self.assertEqual( default_service_tag_import_options._only_add_existing_tags, False )
        
        self.assertEqual( default_service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), set() )
        
    
    def test_get_tags_filtering( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, set() )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), some_tags )
        
        #
        
        only_namespaced = HydrusTags.TagFilter()
        
        only_namespaced.SetRule( '', HC.FILTER_BLACKLIST )
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, get_tags_filter = only_namespaced )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), { 'character:samus aran', 'series:metroid' } )
        
        #
        
        only_samus = HydrusTags.TagFilter()
        
        only_samus.SetRule( '', HC.FILTER_BLACKLIST )
        only_samus.SetRule( ':', HC.FILTER_BLACKLIST )
        only_samus.SetRule( 'character:samus aran', HC.FILTER_WHITELIST )
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, get_tags_filter = only_samus )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), { 'character:samus aran' } )
        
    
    def test_additional( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, set() )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, additional_tags = [ 'wew' ] )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), some_tags.union( [ 'wew' ] ) )
        
    
    def test_overwrite_deleted_get_tags_filtering( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, { 'bodysuit', 'series:metroid' } )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, get_tags_overwrite_deleted = False )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), { 'character:samus aran' } )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, get_tags_overwrite_deleted = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), some_tags )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, additional_tags_overwrite_deleted = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), { 'character:samus aran' } )
        
    
    def test_overwrite_deleted_additional( self ):
        
        some_tags = set()
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, { 'bodysuit', 'series:metroid' } )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, additional_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }, additional_tags_overwrite_deleted = False )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), { 'character:samus aran' } )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, additional_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }, additional_tags_overwrite_deleted = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), { 'bodysuit', 'character:samus aran', 'series:metroid' } )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, additional_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }, get_tags_overwrite_deleted = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), { 'character:samus aran' } )
        
    
    def test_application( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        inbox_media_result = GetTagsMediaResult( example_hash, True, example_service_key, set() )
        archive_media_result = GetTagsMediaResult( example_hash, False, example_service_key, set() )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, to_new_files = True, to_already_in_inbox = False, to_already_in_archive = False )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, inbox_media_result, some_tags ), some_tags )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, inbox_media_result, some_tags ), set() )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, archive_media_result, some_tags ), set() )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, to_new_files = False, to_already_in_inbox = True, to_already_in_archive = False )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, inbox_media_result, some_tags ), set() )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, inbox_media_result, some_tags ), some_tags )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, archive_media_result, some_tags ), set() )
        
        #
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, to_new_files = False, to_already_in_inbox = False, to_already_in_archive = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, inbox_media_result, some_tags ), set() )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, inbox_media_result, some_tags ), set() )
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, archive_media_result, some_tags ), some_tags )
        
    
    def test_existing( self ):
        
        some_tags = { 'bodysuit', 'character:samus aran', 'series:metroid' }
        existing_tags = { 'character:samus aran', 'series:metroid' }
        example_hash = HydrusData.GenerateKey()
        example_service_key = HydrusData.GenerateKey()
        
        media_result = GetTagsMediaResult( example_hash, True, example_service_key, set() )
        
        #
        
        TG.test_controller.SetRead( 'filter_existing_tags', existing_tags )
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, only_add_existing_tags = True )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), existing_tags )
        
        #
        
        some_tags = { 'explicit', 'bodysuit', 'character:samus aran', 'series:metroid' }
        existing_tags = { 'bodysuit' }
        
        only_unnamespaced = HydrusTags.TagFilter()
        
        only_unnamespaced.SetRule( ':', HC.FILTER_BLACKLIST )
        
        TG.test_controller.SetRead( 'filter_existing_tags', existing_tags )
        
        service_tag_import_options = TagImportOptionsLegacy.ServiceTagImportOptions( get_tags = True, only_add_existing_tags = True, only_add_existing_tags_filter = only_unnamespaced )
        
        self.assertEqual( service_tag_import_options.GetTags( example_service_key, CC.STATUS_SUCCESSFUL_AND_NEW, media_result, some_tags ), { 'bodysuit', 'character:samus aran', 'series:metroid' } )
        
    
