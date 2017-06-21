import collections
import HydrusConstants as HC
import os
import TestConstants
import time
import unittest
import HydrusData
import HydrusGlobals as HG
import HydrusNetworking

class TestBandwidthManagement( unittest.TestCase ):
    
    def test_bandwidth_tracker( self ):
        
        bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 0 ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 0 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 1 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 2 ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 2 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 6 ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 6 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 3600 ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 3600 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None ), 0 )
        self.assertAlmostEquals
        #
        
        bandwidth_tracker.ReportDataUsed( 1024 )
        bandwidth_tracker.ReportRequestUsed()
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 0 ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 0 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), 170 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 1 ), 1 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 2 ), 85 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 2 ), 1 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 6 ), 1024 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 6 ), 1 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 3600 ), 1024 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 3600 ), 1 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None ), 1024 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None ), 1 )
        
        #
        
        time.sleep( 5 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 0 ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 0 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), 42 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 1 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 2 ), 85 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 2 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 6 ), 1024 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 6 ), 1 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 3600 ), 1024 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 3600 ), 1 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None ), 1024 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None ), 1 )
        
        #
        
        bandwidth_tracker.ReportDataUsed( 32 )
        bandwidth_tracker.ReportRequestUsed()
        
        bandwidth_tracker.ReportDataUsed( 32 )
        bandwidth_tracker.ReportRequestUsed()
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 0 ), 0 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 0 ), 0 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), 53 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 1 ), 2 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 2 ), 90 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 2 ), 2 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 6 ), 1088 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 6 ), 3 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 3600 ), 1088 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 3600 ), 3 )
        
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None ), 1088 )
        self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None ), 3 )
        
    
