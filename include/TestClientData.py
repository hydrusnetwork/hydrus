import ClientData
import ClientImporting
import os
import unittest

class TestData( unittest.TestCase ):
    
    def test_watcher_options( self ):
        
        regular_watcher_options = ClientData.WatcherOptions( intended_files_per_check = 5, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        fast_watcher_options = ClientData.WatcherOptions( intended_files_per_check = 2, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        slow_watcher_options = ClientData.WatcherOptions( intended_files_per_check = 10, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 86400 ) )
        callous_watcher_options = ClientData.WatcherOptions( intended_files_per_check = 5, never_faster_than = 30, never_slower_than = 86400, death_file_velocity = ( 1, 60 ) )
        
        empty_seed_cache = ClientImporting.SeedCache()
        
        seed_cache = ClientImporting.SeedCache()
        
        last_check_time = 10000000
        
        one_day_before = last_check_time - 86400
        
        for i in range( 50 ):
            
            seed = os.urandom( 16 ).encode( 'hex' )
            
            seed_cache.AddSeeds( ( seed, ) )
            
            seed_cache.UpdateSeedSourceTime( seed, one_day_before - 10 )
            
        
        for i in range( 50 ):
            
            seed = os.urandom( 16 ).encode( 'hex' )
            
            seed_cache.AddSeeds( ( seed, ) )
            
            seed_cache.UpdateSeedSourceTime( seed, one_day_before + 10 )
            
        
        bare_seed_cache = ClientImporting.SeedCache()
        
        bare_seed_cache.AddSeeds( ( 'early', ) )
        bare_seed_cache.AddSeeds( ( 'in_time_delta', ) )
        
        bare_seed_cache.UpdateSeedSourceTime( 'early', one_day_before - 10 )
        bare_seed_cache.UpdateSeedSourceTime( 'in_time_delta', one_day_before + 10 )
        
        busy_seed_cache = ClientImporting.SeedCache()
        
        busy_seed_cache.AddSeeds( ( 'early', ) )
        
        busy_seed_cache.UpdateSeedSourceTime( 'early', one_day_before - 10 )
        
        for i in range( 8640 ):
            
            seed = os.urandom( 16 ).encode( 'hex' )
            
            busy_seed_cache.AddSeeds( ( seed, ) )
            
            busy_seed_cache.UpdateSeedSourceTime( seed, one_day_before + ( ( i + 1 ) * 10 ) - 1 )
            
        
        new_thread_seed_cache = ClientImporting.SeedCache()
        
        for i in range( 10 ):
            
            seed = os.urandom( 16 ).encode( 'hex' )
            
            new_thread_seed_cache.AddSeeds( ( seed, ) )
            
            new_thread_seed_cache.UpdateSeedSourceTime( seed, last_check_time - 600 )
            
        
        # empty
        # should say ok if last_check_time is 0, so it can initialise
        # otherwise sperg out safely
        
        self.assertFalse( regular_watcher_options.IsDead( empty_seed_cache, 0 ) )
        
        self.assertEqual( regular_watcher_options.GetPrettyCurrentVelocity( empty_seed_cache, 0 ), 'no files yet' )
        
        self.assertEqual( regular_watcher_options.GetNextCheckTime( empty_seed_cache, 0 ), 0 )
        
        self.assertTrue( regular_watcher_options.IsDead( empty_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_watcher_options.GetPrettyCurrentVelocity( empty_seed_cache, last_check_time ), 'no files, unable to determine velocity' )
        
        # regular
        # current velocity should be 50 files per day for the day ones and 0 files per min for the callous minute one
        
        self.assertFalse( regular_watcher_options.IsDead( seed_cache, last_check_time ) )
        self.assertFalse( fast_watcher_options.IsDead( seed_cache, last_check_time ) )
        self.assertFalse( slow_watcher_options.IsDead( seed_cache, last_check_time ) )
        self.assertTrue( callous_watcher_options.IsDead( seed_cache, last_check_time ) )
        
        self.assertEqual( regular_watcher_options.GetPrettyCurrentVelocity( seed_cache, last_check_time ), u'at last check, found 50 files in previous 1 day' )
        self.assertEqual( fast_watcher_options.GetPrettyCurrentVelocity( seed_cache, last_check_time ), u'at last check, found 50 files in previous 1 day' )
        self.assertEqual( slow_watcher_options.GetPrettyCurrentVelocity( seed_cache, last_check_time ), u'at last check, found 50 files in previous 1 day' )
        self.assertEqual( callous_watcher_options.GetPrettyCurrentVelocity( seed_cache, last_check_time ), u'at last check, found 0 files in previous 1 minute' )
        
        self.assertEqual( regular_watcher_options.GetNextCheckTime( seed_cache, last_check_time ), last_check_time + 8640 )
        self.assertEqual( fast_watcher_options.GetNextCheckTime( seed_cache, last_check_time ), last_check_time + 3456 )
        self.assertEqual( slow_watcher_options.GetNextCheckTime( seed_cache, last_check_time ), last_check_time + 17280 )
        
        # bare
        # 1 files per day
        
        self.assertFalse( regular_watcher_options.IsDead( bare_seed_cache, last_check_time ) )
        self.assertTrue( callous_watcher_options.IsDead( bare_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_watcher_options.GetPrettyCurrentVelocity( bare_seed_cache, last_check_time ), u'at last check, found 1 files in previous 1 day' )
        
        self.assertEqual( regular_watcher_options.GetNextCheckTime( bare_seed_cache, last_check_time ), last_check_time + 86400 )
        self.assertEqual( fast_watcher_options.GetNextCheckTime( bare_seed_cache, last_check_time ), last_check_time + 86400 )
        self.assertEqual( slow_watcher_options.GetNextCheckTime( bare_seed_cache, last_check_time ), last_check_time + 86400 )
        
        # busy
        # 8640 files per day, 6 files per minute
        
        self.assertFalse( regular_watcher_options.IsDead( busy_seed_cache, last_check_time ) )
        self.assertFalse( fast_watcher_options.IsDead( busy_seed_cache, last_check_time ) )
        self.assertFalse( slow_watcher_options.IsDead( busy_seed_cache, last_check_time ) )
        self.assertFalse( callous_watcher_options.IsDead( busy_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_watcher_options.GetPrettyCurrentVelocity( busy_seed_cache, last_check_time ), u'at last check, found 8,640 files in previous 1 day' )
        self.assertEqual( callous_watcher_options.GetPrettyCurrentVelocity( busy_seed_cache, last_check_time ), u'at last check, found 6 files in previous 1 minute' )
        
        self.assertEqual( regular_watcher_options.GetNextCheckTime( busy_seed_cache, last_check_time ), last_check_time + 50 )
        self.assertEqual( fast_watcher_options.GetNextCheckTime( busy_seed_cache, last_check_time ), last_check_time + 30 )
        self.assertEqual( slow_watcher_options.GetNextCheckTime( busy_seed_cache, last_check_time ), last_check_time + 100 )
        self.assertEqual( callous_watcher_options.GetNextCheckTime( busy_seed_cache, last_check_time ), last_check_time + 50 )
        
        # new thread
        # only had files from ten mins ago, so timings are different
        
        self.assertFalse( regular_watcher_options.IsDead( new_thread_seed_cache, last_check_time ) )
        self.assertFalse( fast_watcher_options.IsDead( new_thread_seed_cache, last_check_time ) )
        self.assertFalse( slow_watcher_options.IsDead( new_thread_seed_cache, last_check_time ) )
        self.assertTrue( callous_watcher_options.IsDead( new_thread_seed_cache, last_check_time ) )
        
        self.assertEqual( regular_watcher_options.GetPrettyCurrentVelocity( new_thread_seed_cache, last_check_time ), u'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( fast_watcher_options.GetPrettyCurrentVelocity( new_thread_seed_cache, last_check_time ), u'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( slow_watcher_options.GetPrettyCurrentVelocity( new_thread_seed_cache, last_check_time ), u'at last check, found 10 files in previous 10 minutes' )
        self.assertEqual( callous_watcher_options.GetPrettyCurrentVelocity( new_thread_seed_cache, last_check_time ), u'at last check, found 0 files in previous 1 minute' )
        
        self.assertEqual( regular_watcher_options.GetNextCheckTime( new_thread_seed_cache, last_check_time ), last_check_time + 300 )
        self.assertEqual( fast_watcher_options.GetNextCheckTime( new_thread_seed_cache, last_check_time ), last_check_time + 120 )
        self.assertEqual( slow_watcher_options.GetNextCheckTime( new_thread_seed_cache, last_check_time ), last_check_time + 600 )
        
    
