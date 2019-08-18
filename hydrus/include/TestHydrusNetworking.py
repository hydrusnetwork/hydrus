import collections
from . import HydrusConstants as HC
import os
import random
import time
import unittest
from . import HydrusData
from . import HydrusGlobals as HG
from . import HydrusNetworking
from mock import patch

now = HydrusData.GetNow()

now_10 = now + 10

now_20 = now + 20

with patch.object( HydrusData, 'GetNow', return_value = now ):
    
    HIGH_USAGE = HydrusNetworking.BandwidthTracker()
    
    for i in range( 100 ):
        
        HIGH_USAGE.ReportRequestUsed()
        HIGH_USAGE.ReportDataUsed( random.randint( 512, 1024 ) )
        
    
    LOW_USAGE = HydrusNetworking.BandwidthTracker()
    
    LOW_USAGE.ReportRequestUsed()
    LOW_USAGE.ReportDataUsed( 1024 )
    
    ZERO_USAGE = HydrusNetworking.BandwidthTracker()
    
class TestBandwidthRules( unittest.TestCase ):
    
    def test_no_rules( self ):
        
        rules = HydrusNetworking.BandwidthRules()
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertTrue( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
    
    def test_per_sec( self ):
        
        # at short time deltas, we can always start based on data alone
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 1, 10240 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertTrue( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertFalse( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertTrue( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertTrue( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        #
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 1, 1 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertFalse( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertTrue( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertTrue( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        #
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 1, 10240 )
        rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 1, 1 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertFalse( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertFalse( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertTrue( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertTrue( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
    
    def test_per_min( self ):
        
        # cutoff is 15s for continue
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 60, 10240 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        #
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 60, 10 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        #
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_DATA, 60, 10240 )
        rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, 60, 10 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
    
    def test_per_month( self ):
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_DATA, None, 10240 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        #
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, None, 10 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        #
        
        rules = HydrusNetworking.BandwidthRules()
        
        rules.AddRule( HC.BANDWIDTH_TYPE_DATA, None, 10240 )
        rules.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, None, 10 )
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_10 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
        with patch.object( HydrusData, 'GetNow', return_value = now_20 ):
            
            self.assertTrue( rules.CanStartRequest( ZERO_USAGE ) )
            self.assertTrue( rules.CanStartRequest( LOW_USAGE ) )
            self.assertFalse( rules.CanStartRequest( HIGH_USAGE ) )
            
            self.assertTrue( rules.CanContinueDownload( ZERO_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( LOW_USAGE ) )
            self.assertTrue( rules.CanContinueDownload( HIGH_USAGE ) )
            
        
    
class TestBandwidthTracker( unittest.TestCase ):
    
    def test_bandwidth_tracker( self ):
        
        bandwidth_tracker = HydrusNetworking.BandwidthTracker()
        
        self.assertEqual( bandwidth_tracker.GetCurrentMonthSummary(), 'used 0B in 0 requests this month' )
        
        now = HydrusData.GetNow()
        
        with patch.object( HydrusData, 'GetNow', return_value = now ):
            
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
            
            #
            
            bandwidth_tracker.ReportDataUsed( 1024 )
            bandwidth_tracker.ReportRequestUsed()
            
            self.assertEqual( bandwidth_tracker.GetCurrentMonthSummary(), 'used 1.0KB in 1 requests this month' )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 0 ), 0 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 0 ), 0 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), 1024 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 1 ), 1 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 2 ), 1024 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 2 ), 1 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 6 ), 1024 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 6 ), 1 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 3600 ), 1024 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 3600 ), 1 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None ), 1024 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None ), 1 )
            
        
        #
        
        five_secs_from_now = now + 5
        
        with patch.object( HydrusData, 'GetNow', return_value = five_secs_from_now ):
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 0 ), 0 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 0 ), 0 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), 0 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 1 ), 0 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 2 ), 0 )
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
            
            self.assertEqual( bandwidth_tracker.GetCurrentMonthSummary(), 'used 1.1KB in 3 requests this month' )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 0 ), 0 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 0 ), 0 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 1 ), 64 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 1 ), 2 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 2 ), 64 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 2 ), 2 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 6 ), 1088 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 6 ), 3 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, 3600 ), 1088 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, 3600 ), 3 )
            
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None ), 1088 )
            self.assertEqual( bandwidth_tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None ), 3 )
            
        
    
