import ClientData
import ClientImporting
import os
import unittest

class TestData( unittest.TestCase ):
    
    def test_checker_options( self ):
        
        regular_checker_options = ClientData.CheckerOptions( intended_files_per_check = 5, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        fast_checker_options = ClientData.CheckerOptions( intended_files_per_check = 2, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        slow_checker_options = ClientData.CheckerOptions( intended_files_per_check = 10, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        callous_checker_options = ClientData.CheckerOptions( intended_files_per_check = 5, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 60 ) )
        
        empty_seed_cache = ClientImporting.SeedCache()
        
        seed_cache = ClientImporting.SeedCache()
        
        last_check_time = 10000000
        
        one_day_before = last_check_time - 86400
        
        for i in range( 50 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).encode( 'hex' )
            
            seed = ClientImporting.Seed( ClientImporting.SEED_TYPE_URL, url )
            
            seed.source_time = one_day_before - 10
            
            seed_cache.AddSeeds( ( seed, ) )
            
        
        for i in range( 50 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).encode( 'hex' )
            
            seed = ClientImporting.Seed( ClientImporting.SEED_TYPE_URL, url )
            
            seed.source_time = last_check_time - 600
            
            seed_cache.AddSeeds( ( seed, ) )
            
        
        bare_seed_cache = ClientImporting.SeedCache()
        
        url = 'https://wew.lad/' + 'early'
        
        seed = ClientImporting.Seed( ClientImporting.SEED_TYPE_URL, url )
        
        seed.source_time = one_day_before - 10
        
        bare_seed_cache.AddSeeds( ( seed, ) )
        
        url = 'https://wew.lad/' + 'in_time_delta'
        
        seed = ClientImporting.Seed( ClientImporting.SEED_TYPE_URL, url )
        
        seed.source_time = one_day_before + 10
        
        bare_seed_cache.AddSeeds( ( seed, ) )
        
        busy_seed_cache = ClientImporting.SeedCache()
        
        url = 'https://wew.lad/' + 'early'
        
        seed = ClientImporting.Seed( ClientImporting.SEED_TYPE_URL, url )
        
        seed.source_time = one_day_before - 10
        
        busy_seed_cache.AddSeeds( ( seed, ) )
        
        for i in range( 8640 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).encode( 'hex' )
            
            seed = ClientImporting.Seed( ClientImporting.SEED_TYPE_URL, url )
            
            seed.source_time = one_day_before + ( ( i + 1 ) * 10 ) - 1
            
            busy_seed_cache.AddSeeds( ( seed, ) )
            
        
        new_thread_seed_cache = ClientImporting.SeedCache()
        
        for i in range( 10 ):
            
            url = 'https://wew.lad/' + os.urandom( 16 ).encode( 'hex' )
            
            seed = ClientImporting.Seed( ClientImporting.SEED_TYPE_URL, url )
            
            seed.source_time = last_check_time - 600
            
            new_thread_seed_cache.AddSeeds( ( seed, ) )
            
        
        # empty
        # should say ok if last_check_time is 0, so it can initialise
        # otherwise sperg out safely
        
        self.assertFalse( regular_checker_options.IsDead( empty_seed_cache, 0 ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( empty_seed_cache, 0 ), 'no files yet' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( empty_seed_cache, 0 ), 0 )
        
        self.assertTrue( regular_checker_options.IsDead( empty_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( empty_seed_cache, last_check_time ), 'no files, unable to determine velocity' )
        
        # regular
        # current velocity should be 50 files per day for the day ones and 0 files per min for the callous minute one
        
        self.assertFalse( regular_checker_options.IsDead( seed_cache, last_check_time ) )
        self.assertFalse( fast_checker_options.IsDead( seed_cache, last_check_time ) )
        self.assertFalse( slow_checker_options.IsDead( seed_cache, last_check_time ) )
        self.assertTrue( callous_checker_options.IsDead( seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( seed_cache, last_check_time ), u'at last check, found 50 files in previous 1 day' )
        self.assertEqual( fast_checker_options.GetPrettyCurrentVelocity( seed_cache, last_check_time ), u'at last check, found 50 files in previous 1 day' )
        self.assertEqual( slow_checker_options.GetPrettyCurrentVelocity( seed_cache, last_check_time ), u'at last check, found 50 files in previous 1 day' )
        self.assertEqual( callous_checker_options.GetPrettyCurrentVelocity( seed_cache, last_check_time ), u'at last check, found 0 files in previous 1 minute' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( seed_cache, last_check_time ), last_check_time + 8640 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( seed_cache, last_check_time ), last_check_time + 3456 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( seed_cache, last_check_time ), last_check_time + 17280 )
        
        # bare
        # 1 files per day
        
        self.assertFalse( regular_checker_options.IsDead( bare_seed_cache, last_check_time ) )
        self.assertTrue( callous_checker_options.IsDead( bare_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( bare_seed_cache, last_check_time ), u'at last check, found 1 files in previous 1 day' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( bare_seed_cache, last_check_time ), last_check_time + 86400 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( bare_seed_cache, last_check_time ), last_check_time + 86400 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( bare_seed_cache, last_check_time ), last_check_time + 86400 )
        
        # busy
        # 8640 files per day, 6 files per minute
        
        self.assertFalse( regular_checker_options.IsDead( busy_seed_cache, last_check_time ) )
        self.assertFalse( fast_checker_options.IsDead( busy_seed_cache, last_check_time ) )
        self.assertFalse( slow_checker_options.IsDead( busy_seed_cache, last_check_time ) )
        self.assertFalse( callous_checker_options.IsDead( busy_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( busy_seed_cache, last_check_time ), u'at last check, found 8,640 files in previous 1 day' )
        self.assertEqual( callous_checker_options.GetPrettyCurrentVelocity( busy_seed_cache, last_check_time ), u'at last check, found 6 files in previous 1 minute' )
        
        self.assertEqual( regular_checker_options.GetNextCheckTime( busy_seed_cache, last_check_time ), last_check_time + 50 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( busy_seed_cache, last_check_time ), last_check_time + 30 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( busy_seed_cache, last_check_time ), last_check_time + 100 )
        self.assertEqual( callous_checker_options.GetNextCheckTime( busy_seed_cache, last_check_time ), last_check_time + 50 )
        
        # new thread
        # only had files from ten mins ago, so timings are different
        
        self.assertFalse( regular_checker_options.IsDead( new_thread_seed_cache, last_check_time ) )
        self.assertFalse( fast_checker_options.IsDead( new_thread_seed_cache, last_check_time ) )
        self.assertFalse( slow_checker_options.IsDead( new_thread_seed_cache, last_check_time ) )
        self.assertTrue( callous_checker_options.IsDead( new_thread_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_checker_options.GetPrettyCurrentVelocity( new_thread_seed_cache, last_check_time ), u'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( fast_checker_options.GetPrettyCurrentVelocity( new_thread_seed_cache, last_check_time ), u'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( slow_checker_options.GetPrettyCurrentVelocity( new_thread_seed_cache, last_check_time ), u'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( callous_checker_options.GetPrettyCurrentVelocity( new_thread_seed_cache, last_check_time ), u'at last check, found 0 files in previous 1 minute' )
        
        # these would be 360, 120, 600, but the 'don't check faster the time since last file post' bumps this up
        self.assertEqual( regular_checker_options.GetNextCheckTime( new_thread_seed_cache, last_check_time ), last_check_time + 600 )
        self.assertEqual( fast_checker_options.GetNextCheckTime( new_thread_seed_cache, last_check_time ), last_check_time + 600 )
        self.assertEqual( slow_checker_options.GetNextCheckTime( new_thread_seed_cache, last_check_time ), last_check_time + 600 )
        
    
