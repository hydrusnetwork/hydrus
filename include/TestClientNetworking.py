from . import ClientConstants as CC
from . import ClientNetworking
from . import ClientNetworkingBandwidth
from . import ClientNetworkingContexts
from . import ClientNetworkingDomain
from . import ClientNetworkingJobs
from . import ClientNetworkingLogin
from . import ClientNetworkingSessions
from . import ClientServices
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusNetworking
import os
from . import TestController
import threading
import time
import unittest
from . import HydrusGlobals as HG
from httmock import all_requests, urlmatch, HTTMock, response
from mock import patch

# some gumpf
GOOD_RESPONSE = bytes( range( 256 ) )

# 256KB of gumpf
LONG_GOOD_RESPONSE = GOOD_RESPONSE * 4 * 256

BAD_RESPONSE = b'500, it done broke'

@all_requests
def catch_all( url, request ):
    
    raise Exception( 'An unexpected request for ' + url + ' came through in testing.' )
    

MOCK_DOMAIN = 'wew.lad'
MOCK_SUBDOMAIN = 'top.wew.lad'
MOCK_URL = 'https://wew.lad/folder/request&key1=value1&key2=value2'
MOCK_SUBURL = 'https://top.wew.lad/folder2/request&key1=value1&key2=value2'

MOCK_HYDRUS_SERVICE_KEY = HydrusData.GenerateKey()
MOCK_HYDRUS_ADDRESS = '123.45.67.89'
MOCK_HYDRUS_DOMAIN = '123.45.67.89:45871'
MOCK_HYDRUS_URL = 'https://123.45.67.89:45871/muh_hydrus_command'

@urlmatch( netloc = 'wew.lad' )
def catch_wew_error( url, request ):
    
    return { 'status_code' : 500, 'reason' : 'Internal Server Error', 'content' : BAD_RESPONSE }

@urlmatch( netloc = 'wew.lad' )
def catch_wew_ok( url, request ):
    
    return GOOD_RESPONSE
    
@urlmatch( netloc = MOCK_HYDRUS_ADDRESS )
def catch_hydrus_error( url, request ):
    
    return response( 500, BAD_RESPONSE, { 'Server' : HC.service_string_lookup[ HC.TAG_REPOSITORY ] + '/' + str( HC.NETWORK_VERSION ) }, 'Internal Server Error' )

@urlmatch( netloc = MOCK_HYDRUS_ADDRESS )
def catch_hydrus_ok( url, request ):
    
    return response( 200, GOOD_RESPONSE, { 'Server' : HC.service_string_lookup[ HC.TAG_REPOSITORY ] + '/' + str( HC.NETWORK_VERSION ) }, 'OK' )
    
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
        
        DOMAIN_NETWORK_CONTEXT = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, MOCK_DOMAIN )
        SUBDOMAIN_NETWORK_CONTEXT = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, MOCK_SUBDOMAIN )
        
        GLOBAL_NETWORK_CONTEXTS = [ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ]
        DOMAIN_NETWORK_CONTEXTS = [ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, DOMAIN_NETWORK_CONTEXT ]
        SUBDOMAIN_NETWORK_CONTEXTS = [ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, DOMAIN_NETWORK_CONTEXT, SUBDOMAIN_NETWORK_CONTEXT ]
        
        #
        
        fast_forward = HydrusData.GetNow() + 3600
        
        with patch.object( HydrusData, 'GetNow', return_value = fast_forward ):
            
            bm = ClientNetworkingBandwidth.NetworkBandwidthManager()
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.ReportRequestUsed( DOMAIN_NETWORK_CONTEXTS )
            bm.ReportDataUsed( DOMAIN_NETWORK_CONTEXTS, 50 )
            bm.ReportRequestUsed( SUBDOMAIN_NETWORK_CONTEXTS )
            bm.ReportDataUsed( SUBDOMAIN_NETWORK_CONTEXTS, 25 )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, EMPTY_RULES )
            bm.SetRules( DOMAIN_NETWORK_CONTEXT, EMPTY_RULES )
            bm.SetRules( SUBDOMAIN_NETWORK_CONTEXT, EMPTY_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, PERMISSIVE_DATA_RULES )
            bm.SetRules( DOMAIN_NETWORK_CONTEXT, PERMISSIVE_DATA_RULES )
            bm.SetRules( SUBDOMAIN_NETWORK_CONTEXT, PERMISSIVE_DATA_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, PERMISSIVE_REQUEST_RULES )
            bm.SetRules( DOMAIN_NETWORK_CONTEXT, PERMISSIVE_REQUEST_RULES )
            bm.SetRules( SUBDOMAIN_NETWORK_CONTEXT, PERMISSIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.SetRules( SUBDOMAIN_NETWORK_CONTEXT, RESTRICTIVE_DATA_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( SUBDOMAIN_NETWORK_CONTEXT, RESTRICTIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( SUBDOMAIN_NETWORK_CONTEXT, PERMISSIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.SetRules( DOMAIN_NETWORK_CONTEXT, RESTRICTIVE_DATA_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( DOMAIN_NETWORK_CONTEXT, RESTRICTIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( DOMAIN_NETWORK_CONTEXT, PERMISSIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, RESTRICTIVE_DATA_RULES )
            
            self.assertFalse( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, RESTRICTIVE_REQUEST_RULES )
            
            self.assertFalse( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            bm.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, PERMISSIVE_REQUEST_RULES )
            
            self.assertTrue( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertTrue( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
            #
            
            bm.SetRules( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT, RESTRICTIVE_DATA_RULES )
            bm.SetRules( DOMAIN_NETWORK_CONTEXT, RESTRICTIVE_REQUEST_RULES )
            bm.SetRules( DOMAIN_NETWORK_CONTEXT, EMPTY_RULES )
            
            self.assertFalse( bm.CanStartRequest( GLOBAL_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( DOMAIN_NETWORK_CONTEXTS ) )
            self.assertFalse( bm.CanStartRequest( SUBDOMAIN_NETWORK_CONTEXTS ) )
            
        
    
    def test_can_continue( self ):
        
        pass
        
    
class TestNetworkingEngine( unittest.TestCase ):
    
    def test_engine_shutdown_app( self ):
        
        mock_controller = TestController.MockController()
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        self.assertFalse( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        mock_controller.CallToThread( engine.MainLoop )
        
        time.sleep( 0.1 )
        
        self.assertTrue( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        mock_controller.model_is_shutdown = True
        
        engine._new_work_to_do.set()
        
        time.sleep( 0.1 )
        
        self.assertFalse( engine.IsRunning() )
        self.assertTrue( engine.IsShutdown() )
        
    
    def test_engine_shutdown_manual( self ):
        
        mock_controller = TestController.MockController()
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        self.assertFalse( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        mock_controller.CallToThread( engine.MainLoop )
        
        time.sleep( 0.1 )
        
        self.assertTrue( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        engine.Shutdown()
        
        time.sleep( 0.1 )
        
        self.assertFalse( engine.IsRunning() )
        self.assertTrue( engine.IsShutdown() )
        
    
    def test_engine_simple_job( self ):
        
        mock_controller = TestController.MockController()
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        self.assertFalse( engine.IsRunning() )
        self.assertFalse( engine.IsShutdown() )
        
        mock_controller.CallToThread( engine.MainLoop )
        
        #
        
        with HTTMock( catch_all ):
            
            with HTTMock( catch_wew_ok ):
                
                job = ClientNetworkingJobs.NetworkJob( 'GET', MOCK_URL )
                
                engine.AddJob( job )
                
                time.sleep( 0.25 )
                
                self.assertTrue( job.IsDone() )
                self.assertFalse( job.HasError() )
                
                engine._new_work_to_do.set()
                
                time.sleep( 0.25 )
                
                self.assertEqual( len( engine._jobs_awaiting_validity ), 0 )
                self.assertEqual( len( engine._jobs_awaiting_bandwidth ), 0 )
                self.assertEqual( len( engine._jobs_awaiting_login ), 0 )
                self.assertEqual( len( engine._jobs_awaiting_slot ), 0 )
                self.assertEqual( len( engine._jobs_running ), 0 )
                
            
        
        #
        
        engine.Shutdown()
        
    
class TestNetworkingJob( unittest.TestCase ):
    
    def _GetJob( self, for_login = False ):
        
        job = ClientNetworkingJobs.NetworkJob( 'GET', MOCK_URL )
        
        job.SetForLogin( for_login )
        
        mock_controller = TestController.MockController()
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, domain_manager, login_manager )
        
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
            
        
    
    def test_bandwidth_exceeded( self ):
        
        RESTRICTIVE_DATA_RULES = HydrusNetworking.BandwidthRules()
        
        RESTRICTIVE_DATA_RULES.AddRule( HC.BANDWIDTH_TYPE_DATA, None, 10 )
        
        DOMAIN_NETWORK_CONTEXT = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, MOCK_DOMAIN )
        
        #
        
        job = self._GetJob()
        
        self.assertEqual( job.BandwidthOK(), True )
        
        job.engine.bandwidth_manager.ReportDataUsed( [ DOMAIN_NETWORK_CONTEXT ], 50 )
        
        job.engine.bandwidth_manager.SetRules( DOMAIN_NETWORK_CONTEXT, RESTRICTIVE_DATA_RULES )
        
        self.assertEqual( job.BandwidthOK(), False )
        
        #
        
        job = self._GetJob( for_login = True )
        
        self.assertEqual( job.BandwidthOK(), True )
        
        job.engine.bandwidth_manager.ReportDataUsed( [ DOMAIN_NETWORK_CONTEXT ], 50 )
        
        job.engine.bandwidth_manager.SetRules( DOMAIN_NETWORK_CONTEXT, RESTRICTIVE_DATA_RULES )
        
        self.assertEqual( job.BandwidthOK(), True )
        
    
    def test_bandwidth_ok( self ):
        
        PERMISSIVE_DATA_RULES = HydrusNetworking.BandwidthRules()
        
        PERMISSIVE_DATA_RULES.AddRule( HC.BANDWIDTH_TYPE_DATA, None, 1048576 )
        
        DOMAIN_NETWORK_CONTEXT = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_DOMAIN, MOCK_DOMAIN )
        
        #
        
        job = self._GetJob()
        
        job.engine.bandwidth_manager.ReportDataUsed( [ DOMAIN_NETWORK_CONTEXT ], 50 )
        
        self.assertEqual( job.BandwidthOK(), True )
        
        job.engine.bandwidth_manager.SetRules( DOMAIN_NETWORK_CONTEXT, PERMISSIVE_DATA_RULES )
        
        self.assertEqual( job.BandwidthOK(), True )
        
        #
        
        job = self._GetJob( for_login = True )
        
        job.engine.bandwidth_manager.ReportDataUsed( [ DOMAIN_NETWORK_CONTEXT ], 50 )
        
        self.assertEqual( job.BandwidthOK(), True )
        
        job.engine.bandwidth_manager.SetRules( DOMAIN_NETWORK_CONTEXT, PERMISSIVE_DATA_RULES )
        
        self.assertEqual( job.BandwidthOK(), True )
        
    
    def test_bandwidth_reported( self ):
        
        with HTTMock( catch_all ):
            
            with HTTMock( catch_wew_ok ):
                
                job = self._GetJob()
                
                job.BandwidthOK()
                
                job.Start()
                
                bm = job.engine.bandwidth_manager
                
                tracker = bm.GetTracker( ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT )
                
                self.assertTrue( tracker.GetUsage( HC.BANDWIDTH_TYPE_REQUESTS, None ), 1 )
                self.assertTrue( tracker.GetUsage( HC.BANDWIDTH_TYPE_DATA, None ), 256 )
                
            
        
    
    def test_done_ok( self ):
        
        with HTTMock( catch_all ):
            
            with HTTMock( catch_wew_ok ):
                
                job = self._GetJob()
                
                job.Start()
                
                self.assertFalse( job.HasError() )
                
                self.assertEqual( job.GetContentBytes(), GOOD_RESPONSE )
                
                self.assertEqual( job.GetStatus(), ( 'done!', 256, 256, None ) )
                
            
        
    
    def test_error( self ):
        
        with HTTMock( catch_all ):
            
            with HTTMock( catch_wew_error ):
                
                job = self._GetJob()
                
                job.Start()
                
                self.assertTrue( job.HasError() )
                
                self.assertEqual( job.GetContentBytes(), BAD_RESPONSE )
                
                self.assertEqual( type( job.GetErrorException() ), HydrusExceptions.ServerException )
                
                self.assertTrue( job.GetErrorText(), BAD_RESPONSE )
                
                self.assertEqual( job.GetStatus(), ( '500 - Internal Server Error', 18, 18, None ) )
                
            
        
    
    def test_generate_login_process( self ):
        
        # test the system works as expected
        
        pass
        
    
    def test_needs_login( self ):
        
        # test for both normal and login
        
        pass
        
    
class TestNetworkingJobHydrus( unittest.TestCase ):
    
    def _GetJob( self, for_login = False ):
        
        job = ClientNetworkingJobs.NetworkJobHydrus( MOCK_HYDRUS_SERVICE_KEY, 'GET', MOCK_HYDRUS_URL )
        
        job.SetForLogin( for_login )
        
        mock_controller = TestController.MockController()
        
        mock_service = ClientServices.GenerateService( MOCK_HYDRUS_SERVICE_KEY, HC.TAG_REPOSITORY, 'test tag repo' )
        
        mock_services_manager = TestController.MockServicesManager( ( mock_service, ) )
        
        mock_controller.services_manager = mock_services_manager
        
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        job.engine = engine
        
        return job
        
    
    def test_bandwidth_exceeded( self ):
        
        RESTRICTIVE_DATA_RULES = HydrusNetworking.BandwidthRules()
        
        RESTRICTIVE_DATA_RULES.AddRule( HC.BANDWIDTH_TYPE_DATA, None, 10 )
        
        HYDRUS_NETWORK_CONTEXT = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, MOCK_HYDRUS_SERVICE_KEY )
        
        #
        
        job = self._GetJob()
        
        self.assertEqual( job.BandwidthOK(), True )
        
        job.engine.bandwidth_manager.ReportDataUsed( [ HYDRUS_NETWORK_CONTEXT ], 50 )
        
        job.engine.bandwidth_manager.SetRules( HYDRUS_NETWORK_CONTEXT, RESTRICTIVE_DATA_RULES )
        
        self.assertEqual( job.BandwidthOK(), False )
        
        #
        
        job = self._GetJob( for_login = True )
        
        self.assertEqual( job.BandwidthOK(), True )
        
        job.engine.bandwidth_manager.ReportDataUsed( [ HYDRUS_NETWORK_CONTEXT ], 50 )
        
        job.engine.bandwidth_manager.SetRules( HYDRUS_NETWORK_CONTEXT, RESTRICTIVE_DATA_RULES )
        
        self.assertEqual( job.BandwidthOK(), True )
        
    
    def test_bandwidth_ok( self ):
        
        PERMISSIVE_DATA_RULES = HydrusNetworking.BandwidthRules()
        
        PERMISSIVE_DATA_RULES.AddRule( HC.BANDWIDTH_TYPE_DATA, None, 1048576 )
        
        HYDRUS_NETWORK_CONTEXT = ClientNetworkingContexts.NetworkContext( CC.NETWORK_CONTEXT_HYDRUS, MOCK_HYDRUS_SERVICE_KEY )
        
        #
        
        job = self._GetJob()
        
        job.engine.bandwidth_manager.ReportDataUsed( [ HYDRUS_NETWORK_CONTEXT ], 50 )
        
        self.assertEqual( job.BandwidthOK(), True )
        
        job.engine.bandwidth_manager.SetRules( HYDRUS_NETWORK_CONTEXT, PERMISSIVE_DATA_RULES )
        
        self.assertEqual( job.BandwidthOK(), True )
        
        #
        
        job = self._GetJob( for_login = True )
        
        job.engine.bandwidth_manager.ReportDataUsed( [ HYDRUS_NETWORK_CONTEXT ], 50 )
        
        self.assertEqual( job.BandwidthOK(), True )
        
        job.engine.bandwidth_manager.SetRules( HYDRUS_NETWORK_CONTEXT, PERMISSIVE_DATA_RULES )
        
        self.assertEqual( job.BandwidthOK(), True )
        
    
    def test_bandwidth_reported( self ):
        
        pass
        
    
    def test_done_ok( self ):
        
        with HTTMock( catch_all ):
            
            with HTTMock( catch_hydrus_ok ):
                
                job = self._GetJob()
                
                job.Start()
                
                self.assertFalse( job.HasError() )
                
                self.assertEqual( job.GetContentBytes(), GOOD_RESPONSE )
                
                self.assertEqual( job.GetStatus(), ( 'done!', 256, 256, None ) )
                
            
        
    
    def test_error( self ):
        
        with HTTMock( catch_all ):
            
            with HTTMock( catch_hydrus_error ):
                
                job = self._GetJob()
                
                job.Start()
                
                self.assertTrue( job.HasError() )
                
                self.assertEqual( job.GetContentBytes(), BAD_RESPONSE )
                
                self.assertEqual( type( job.GetErrorException() ), HydrusExceptions.ServerException )
                
                self.assertTrue( job.GetErrorText(), BAD_RESPONSE )
                
                self.assertEqual( job.GetStatus(), ( '500 - Internal Server Error', 18, 18, None ) )
                
            
        
    
    def test_generate_login_process( self ):
        
        # test the system works as expected
        
        pass
        
    
    def test_needs_login( self ):
        
        # test for both normal and login
        
        pass
        
    
