import ClientConstants as CC
import ClientNetworking
import collections
import HydrusConstants as HC
import HydrusData
import HydrusNetworking
import os
import TestConstants
import threading
import time
import unittest
import HydrusGlobals as HG
from httmock import all_requests, urlmatch, HTTMock
from mock import patch

# some gumpf
GOOD_RESPONSE = ''.join( chr( i ) for i in range( 256 ) )

# 256KB of gumpf
LONG_GOOD_RESPONSE = GOOD_RESPONSE * 4 * 256

@all_requests
def catch_all( url, request ):
    
    raise Exception( 'An unexpected request for ' + url + ' came through in testing.' )
    

MOCK_DOMAIN = 'wew.lad'
MOCK_SUBDOMAIN = 'top.wew.lad'
MOCK_URL = 'https://wew.lad/folder/request&key1=value1&key2=value2'
MOCK_SUBURL = 'https://top.wew.lad/folder2/request&key1=value1&key2=value2'

@urlmatch( netloc = 'wew.lad' )
def catch_wew_ok( url, request ):
    
    return GOOD_RESPONSE
    
@urlmatch( netloc = '123.45.67.89:45871' )
def catch_hydrus_ok( url, request ):
    
    return GOOD_RESPONSE
    
class TestBandwidthManager( unittest.TestCase ):
    
    def test_can_start( self ):
        
        EMPTY_RULES = HydrusNetworking.BandwidthRules()
        
        PERMISSIVE_DATA_RULES = HydrusNetworking.BandwidthRules()
        
        PERMISSIVE_DATA_RULES.AddRule( HC.BANDWIDTH_TYPE_DATA, None, 1048576 )
        
        PERMISSIVE_REQUEST_RULES = HydrusNetworking.BandwidthRules()
        
        PERMISSIVE_REQUEST_RULES.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, None, 10000 )
        
        RESTRICTIVE_DATA_RULES = HydrusNetworking.BandwidthRules()
        
        RESTRICTIVE_DATA_RULES.AddRule( HC.BANDWIDTH_TYPE_DATA, None, 10 )
        
        RESTRICTIVE_REQUEST_RULES = HydrusNetworking.BandwidthRules()
        
        RESTRICTIVE_REQUEST_RULES.AddRule( HC.BANDWIDTH_TYPE_REQUESTS, None, 1 )
        
        DOMAIN_NETWORK_CONTEXT = ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, MOCK_DOMAIN )
        SUBDOMAIN_NETWORK_CONTEXT = ClientNetworking.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, MOCK_SUBDOMAIN )
        
        GLOBAL_NETWORK_CONTEXTS = [ ClientNetworking.GLOBAL_NETWORK_CONTEXT ]
        DOMAIN_NETWORK_CONTEXTS = [ ClientNetworking.GLOBAL_NETWORK_CONTEXT, DOMAIN_NETWORK_CONTEXT ]
        SUBDOMAIN_NETWORK_CONTEXTS = [ ClientNetworking.GLOBAL_NETWORK_CONTEXT, DOMAIN_NETWORK_CONTEXT, SUBDOMAIN_NETWORK_CONTEXT ]
        #
        
        fast_forward = HydrusData.GetNow() + 3600
        
        with patch.object( HydrusData, 'GetNow', return_value = fast_forward ):
            
            bm = ClientNetworking.NetworkBandwidthManager()
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.ReportRequestUsed( DOMAIN_NETWORK_CONTEXTS )
            bm.ReportDataUsed( DOMAIN_NETWORK_CONTEXTS, 50 )
            bm.ReportRequestUsed( SUBDOMAIN_NETWORK_CONTEXTS )
            bm.ReportDataUsed( SUBDOMAIN_NETWORK_CONTEXTS, 25 )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.SetRules( None, EMPTY_RULES )
            bm.SetRules( MOCK_DOMAIN, EMPTY_RULES )
            bm.SetRules( MOCK_SUBDOMAIN, EMPTY_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( None, PERMISSIVE_DATA_RULES )
            bm.SetRules( MOCK_DOMAIN, PERMISSIVE_DATA_RULES )
            bm.SetRules( MOCK_SUBDOMAIN, PERMISSIVE_DATA_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( None, PERMISSIVE_REQUEST_RULES )
            bm.SetRules( MOCK_DOMAIN, PERMISSIVE_REQUEST_RULES )
            bm.SetRules( MOCK_SUBDOMAIN, PERMISSIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.SetRules( MOCK_SUBDOMAIN, RESTRICTIVE_DATA_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( MOCK_SUBDOMAIN, RESTRICTIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( MOCK_SUBDOMAIN, PERMISSIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.SetRules( MOCK_DOMAIN, RESTRICTIVE_DATA_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( MOCK_DOMAIN, RESTRICTIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( MOCK_DOMAIN, PERMISSIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( MOCK_SUBDOMAIN ) )
            
            #
            
            bm.SetRules( None, RESTRICTIVE_DATA_RULES )
            
            self.assertFalse( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( None, RESTRICTIVE_REQUEST_RULES )
            
            self.assertFalse( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( None, PERMISSIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStart( MOCK_SUBDOMAIN ) )
            
            # add some rules for all
            
            bm.SetRules( None, RESTRICTIVE_DATA_RULES )
            bm.SetRules( MOCK_DOMAIN, RESTRICTIVE_REQUEST_RULES )
            bm.SetRules( MOCK_DOMAIN, EMPTY_RULES )
            
            self.assertFalse( bm.CanStart( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStart( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
        
    
    def test_can_continue( self ):
        
        pass
        
    
class TestNetworkingEngine( unittest.TestCase ):
    
    def test_engine_shutdown_app( self ):
        
        mock_controller = TestConstants.MockController()
        bandwidth_manager = ClientNetworking.NetworkBandwidthManager()
        session_manager = ClientNetworking.NetworkSessionManager()
        login_manager = ClientNetworking.NetworkLoginManager()
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, login_manager )
        
        self.assertFalse( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        engine.Start()
        
        time.sleep( 0.1 )
        
        self.assertTrue( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        mock_controller.model_is_shutdown = True
        
        engine._new_work_to_do.set()
        
        time.sleep( 0.1 )
        
        self.assertFalse( engine.IsRunning() )
        self.assertTrue( engine.IsShutdown() )
        
    
    def test_engine_shutdown_manual( self ):
        
        mock_controller = TestConstants.MockController()
        bandwidth_manager = ClientNetworking.NetworkBandwidthManager()
        session_manager = ClientNetworking.NetworkSessionManager()
        login_manager = ClientNetworking.NetworkLoginManager()
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, login_manager )
        
        self.assertFalse( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        engine.Start()
        
        time.sleep( 0.1 )
        
        self.assertTrue( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        engine.Shutdown()
        
        time.sleep( 0.1 )
        
        self.assertFalse( engine.IsRunning() )
        self.assertTrue( engine.IsShutdown() )
        
    
class TestNetworkingJob( unittest.TestCase ):
    
    def _GetJob( self ):
        
        job = ClientNetworking.NetworkJob( 'GET', MOCK_URL )
        
        mock_controller = TestConstants.MockController()
        bandwidth_manager = ClientNetworking.NetworkBandwidthManager()
        session_manager = ClientNetworking.NetworkSessionManager()
        login_manager = ClientNetworking.NetworkLoginManager()
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, login_manager )
        
        job.engine = engine
        
        return job
        
    
    def test_cancelled_manually( self ):
        
        job = self._GetJob()
        
        self.assertFalse( job.IsCancelled() )
        self.assertFalse( job.IsDone() )
        
        job.Cancel()
        
        self.assertTrue( job.IsCancelled() )
        self.assertTrue( job.IsDone() )
        
    
    def test_cancelled_app_shutdown( self ):
        
        job = self._GetJob()
        
        self.assertFalse( job.IsCancelled() )
        self.assertFalse( job.IsDone() )
        
        job.engine.controller.model_is_shutdown = True
        
        self.assertTrue( job.IsCancelled() )
        self.assertTrue( job.IsDone() )
        
    
    def test_sleep( self ):
        
        job = self._GetJob()
        
        self.assertFalse( job.IsAsleep() )
        
        job.Sleep( 3 )
        
        self.assertTrue( job.IsAsleep() )
        
        five_secs_from_now = HydrusData.GetNow() + 5
        
        with patch.object( HydrusData, 'GetNow', return_value = five_secs_from_now ):
            
            self.assertFalse( job.IsAsleep() )
            
        
    
class TestNetworkingJobWeb( unittest.TestCase ):
    
    def _GetJob( self ):
        
        job = ClientNetworking.NetworkJob( 'GET', MOCK_URL )
        
        controller = TestConstants.MockController()
        
        job.controller = controller
        
        return job
        
    
    def test_bandwidth_ok( self ):
        
        # test bandwidth override
        
        # test bandwidth ok
        # test it not ok
        
        # repeat for the login one
        
        pass
        
    
    def test_done_ok( self ):
        
        return # need to flush out session, bandwidth, login code
        
        with HTTMock( catch_all ):
            
            with HTTMock( catch_wew_ok ):
                
                job = self._GetJob()
                
                job.Start()
                
                self.assertFalse( job.HasError() )
                
                self.assertEqual( job.GetContent(), GOOD_RESPONSE )
                
            
        
    
    def test_error( self ):
        
        job = self._GetJob()
        
        # do a requests job that cancels
        
        # haserror
        # geterrorexception
        # geterrortext
        
    
    def test_generate_login_process( self ):
        
        # test the system works as expected
        
        pass
        
    
    def test_needs_login( self ):
        
        # test for both normal and login
        
        pass
        
    
class TestNetworkingJobHydrus( unittest.TestCase ):
    
    def _GetJob( self ):
        
        job = ClientNetworking.NetworkJob( 'GET', 'https://123.45.67.89:45871/muh_hydrus_command' )
        
        controller = TestConstants.MockController()
        
        job.controller = controller
        
        return job
        
    
    def test_bandwidth_ok( self ):
        
        # test bandwidth override
        
        # test bandwidth ok
        # test it not ok
        
        # repeat for the login one
        
        pass
        
    
    def test_done_ok( self ):
        
        return # need to flush out session, bandwidth, login code
        
        with HTTMock( catch_all ):
            
            with HTTMock( catch_hydrus_ok ):
                
                job = self._GetJob()
                
                job.Start()
                
                self.assertFalse( job.HasError() )
                
                self.assertEqual( job.GetContent(), GOOD_RESPONSE )
                
            
        
    
    def test_error( self ):
        
        job = self._GetJob()
        
        # do a requests job that cancels
        
        # haserror
        # geterrorexception
        # geterrortext
        
    
    def test_generate_login_process( self ):
        
        # test the system works as expected
        
        pass
        
    
    def test_needs_login( self ):
        
        # test for both normal and login
        
        pass
        
    
