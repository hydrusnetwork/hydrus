import random
import unittest

from unittest import mock
from httmock import all_requests

from hydrus.core import HydrusData
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientDefaults
from hydrus.client.importing import ClientImportFileSeeds
from hydrus.client.importing import ClientImportGallerySeeds
from hydrus.client.importing import ClientImportSubscriptionQuery
from hydrus.client.importing.options import ClientImportOptions
from hydrus.client.networking import ClientNetworking
from hydrus.client.networking import ClientNetworkingBandwidth
from hydrus.client.networking import ClientNetworkingDomain
from hydrus.client.networking import ClientNetworkingLogin
from hydrus.client.networking import ClientNetworkingSessions

from hydrus.test import TestController

MISSING_RESPONSE = '404, bad result'
ERROR_RESPONSE = '500, it done broke'

EMPTY_RESPONSE = '''<html>
  <head>
    <title>results</title>
  </head>
  <body>
  </body>
</html>'''

@all_requests
def catch_all( url, request ):
    
    raise Exception( 'An unexpected request for ' + url + ' came through in testing.' )
    
def get_good_response( urls_to_place ):
    
    response = '''<html>
  <head>
    <title>results</title>
  </head>
  <body>'''
    
    for url in urls_to_place:
        
        response += '''      <span class="thumb">
        <a href="'''
        
        response += url
        
        response += '''">
            <img src="blah" />
        </a>
      </span>'''
        
    
    response += '''  </body>
</html>'''
    
    return response

class TestSubscription( unittest.TestCase ):
    
    def _PrepEngine( self ):
        
        mock_controller = TestController.MockController()
        bandwidth_manager = ClientNetworkingBandwidth.NetworkBandwidthManager()
        session_manager = ClientNetworkingSessions.NetworkSessionManager()
        domain_manager = ClientNetworkingDomain.NetworkDomainManager()
        login_manager = ClientNetworkingLogin.NetworkLoginManager()
        
        ClientDefaults.SetDefaultDomainManagerData( domain_manager )
        
        engine = ClientNetworking.NetworkEngine( mock_controller, bandwidth_manager, session_manager, domain_manager, login_manager )
        
        mock_controller.CallToThread( engine.MainLoop )
        
        return ( mock_controller, engine )
        
    
    def test_initial_sync( self ):
        
        # TODO: coming back to this later, it obviously isn't really happening.
        # this is good evidence the whole sub system is too tightly coupled, which is how we got 'ispaused' issues in v667 and two hotfixes
        
        # wait until I have searcher in here, so I can roll it all into domain_manager etc... rather than hitting db for gallery init and all that
        
        # use pseudo html documents here that work with the parsers
        
        # 404 all file pages for now
        
        # refer to testclientnetworking for useful httmock examples
        
        # test:
        # initial is good to go with right stuff set up
        # a 404 gallery on initial
        # a 500 gallery on initial
        # a 200 gallery but empty result on initial
        # a 200 gallery typical good initial sync involving several pages
        # a subsequent 50 catch-up involving two pages
        # a user cancel on init
        # a user cancel on catch-up
        
        pass
        
    

PRETEND_NOW = 150000000

def flesh_out_with_stuff(
    query_header: ClientImportSubscriptionQuery.SubscriptionQueryHeader,
    checker_options: ClientImportOptions.CheckerOptions,
    query_log_container: ClientImportSubscriptionQuery.SubscriptionQueryLogContainer,
    with_outstanding_files: bool,
    is_dead: bool
):
    
    query_text = query_header.GetQueryText()
    
    gallery_seed_log = query_log_container.GetGallerySeedLog()
    file_seed_cache = query_log_container.GetFileSeedCache()
    
    current_time = PRETEND_NOW - ( 10 * 86400 )
    current_id = 120000
    
    with mock.patch.object( HydrusTime, 'GetNow', side_effect = lambda: current_time ):
        
        for i in range( 5 ):
            
            gallery_seed = ClientImportGallerySeeds.GallerySeed( f'http://example.com/posts/{query_text}?page=0', can_generate_more_pages = True )
            
            gallery_seed.SetStatus( CC.STATUS_SUCCESSFUL_AND_NEW, 'checked ok, found x new files' )
            
            gallery_seed_log.AddGallerySeeds( [ gallery_seed ] )
            
            for j in range( 10 ):
                
                file_seed = ClientImportFileSeeds.FileSeed( file_seed_type = ClientImportFileSeeds.FILE_SEED_TYPE_URL, file_seed_data = f'https://example.com/post/{current_id}' )
                
                if with_outstanding_files and i == 4:
                    
                    pass
                    
                else:
                    
                    status = random.choice( ( CC.STATUS_SUCCESSFUL_AND_NEW, CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, CC.STATUS_DELETED ) )
                    
                    file_seed.SetStatus( status, 'job done mate' )
                    
                
                file_seed_cache.AddFileSeeds( [ file_seed ] )
                
                current_id -= 5
                
            
            if is_dead and i == 4:
                
                current_time += 86400 * 500
                
                query_header.RegisterSyncComplete( checker_options, query_log_container )
                
            else:
                
                query_header.RegisterSyncComplete( checker_options, query_log_container )
                
            
            current_time += 86400
            
        
    

def generate_query_header( query_text: str, checker_options: ClientImportOptions.CheckerOptions, query_log_container: ClientImportSubscriptionQuery.SubscriptionQueryLogContainer ) -> ClientImportSubscriptionQuery.SubscriptionQueryHeader:
    
    query_header = ClientImportSubscriptionQuery.SubscriptionQueryHeader()
    
    query_header.SetQueryText( query_text )
    
    with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW - 6000 ):
        
        query_header.SyncToQueryLogContainer( checker_options, query_log_container )
        
    
    return query_header
    

def generate_query_log_container() -> ClientImportSubscriptionQuery.SubscriptionQueryLogContainer:
    
    query_log_container = ClientImportSubscriptionQuery.SubscriptionQueryLogContainer( HydrusData.GenerateKey().hex() )
    
    return query_log_container
    

def generate_typical_checker_options() -> ClientImportOptions.CheckerOptions:
    
    return ClientImportOptions.CheckerOptions( intended_files_per_check = 4, never_faster_than = 86400, never_slower_than = 90 * 86400, death_file_velocity = ( 1, 180 * 86400 ) )
    

def generate_empty_query_header( query_text: str ) -> ClientImportSubscriptionQuery.SubscriptionQueryHeader:
    
    checker_options = generate_typical_checker_options()
    query_log_container = generate_query_log_container()
    
    query_header = generate_query_header( query_text, checker_options, query_log_container )
    
    return query_header
    

def generate_fleshed_out_query_header( query_text: str, with_outstanding_files: bool = False, is_dead: bool = False ) -> ClientImportSubscriptionQuery.SubscriptionQueryHeader:
    
    checker_options = generate_typical_checker_options()
    query_log_container = generate_query_log_container()
    
    query_header = generate_query_header( query_text, checker_options, query_log_container )
    
    flesh_out_with_stuff( query_header, checker_options, query_log_container, with_outstanding_files, is_dead )
    
    return query_header
    

class TestSubscriptionQuery( unittest.TestCase ):
    
    def test_pause( self ):
        
        query_header = generate_empty_query_header( 'cool_stuff' )
        
        self.assertFalse( query_header.IsPaused() )
        
        query_header.SetPaused( True )
        
        self.assertTrue( query_header.IsPaused() )
        
        query_header.SetPaused( False )
        
        self.assertFalse( query_header.IsPaused() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cooler_stuff' )
        
        self.assertFalse( query_header.IsPaused() )
        
        query_header.SetPaused( True )
        
        self.assertTrue( query_header.IsPaused() )
        
        query_header.SetPaused( False )
        
        self.assertFalse( query_header.IsPaused() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', is_dead = True )
        
        self.assertTrue( query_header.IsPaused() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True, is_dead = True )
        
        self.assertFalse( query_header.IsPaused() )
        
    
    def test_dead( self ):
        
        query_header = generate_empty_query_header( 'cool_stuff' )
        
        self.assertFalse( query_header.IsDead() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cooler_stuff' )
        
        self.assertFalse( query_header.IsDead() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True )
        
        self.assertFalse( query_header.IsDead() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', is_dead = True )
        
        self.assertTrue( query_header.IsDead() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True, is_dead = True )
        
        self.assertTrue( query_header.IsDead() )
        
    
    def test_outstanding_file_work( self ):
        
        query_header = generate_empty_query_header( 'cool_stuff' )
        
        self.assertFalse( query_header.HasFileWorkToDo() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cooler_stuff' )
        
        self.assertFalse( query_header.HasFileWorkToDo() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True )
        
        self.assertTrue( query_header.HasFileWorkToDo() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', is_dead = True )
        
        self.assertFalse( query_header.HasFileWorkToDo() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True, is_dead = True )
        
        self.assertTrue( query_header.HasFileWorkToDo() )
        
    
    def test_sync_due( self ):
        
        query_header = generate_empty_query_header( 'cool_stuff' )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cooler_stuff' )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() + 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() - 5 ):
            
            self.assertFalse( query_header.IsSyncDue() )
            
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() + 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() - 5 ):
            
            self.assertFalse( query_header.IsSyncDue() )
            
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', is_dead = True )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertFalse( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() + 5 ):
            
            self.assertFalse( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() - 5 ):
            
            self.assertFalse( query_header.IsSyncDue() )
            
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True, is_dead = True )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertFalse( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() + 5 ):
            
            self.assertFalse( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() - 5 ):
            
            self.assertFalse( query_header.IsSyncDue() )
            
        
    
    def test_check_now( self ):
        
        query_header = generate_empty_query_header( 'cool_stuff' )
        
        self.assertFalse( query_header.IsCheckingNow() )
        
        query_header.CheckNow()
        
        self.assertTrue( query_header.IsCheckingNow() )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cooler_stuff' )
        
        self.assertFalse( query_header.IsCheckingNow() )
        
        query_header.CheckNow()
        
        self.assertTrue( query_header.IsCheckingNow() )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() + 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() - 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True )
        
        self.assertFalse( query_header.IsCheckingNow() )
        
        query_header.CheckNow()
        
        self.assertTrue( query_header.IsCheckingNow() )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() + 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() - 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', is_dead = True )
        
        self.assertFalse( query_header.IsCheckingNow() )
        
        query_header.CheckNow()
        
        self.assertTrue( query_header.IsCheckingNow() )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() + 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() - 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True, is_dead = True )
        
        self.assertFalse( query_header.IsCheckingNow() )
        
        query_header.CheckNow()
        
        self.assertTrue( query_header.IsCheckingNow() )
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = PRETEND_NOW ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() + 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
        with mock.patch.object( HydrusTime, 'GetNow', return_value = query_header.GetNextCheckTime() - 5 ):
            
            self.assertTrue( query_header.IsSyncDue() )
            
        
    
    def test_is_expecting_to_work( self ):
        
        query_header = generate_empty_query_header( 'cool_stuff' )
        
        self.assertTrue( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetPaused( True )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetPaused( False )
        
        self.assertTrue( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_MISSING )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cooler_stuff' )
        
        self.assertTrue( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetPaused( True )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetPaused( False )
        
        self.assertTrue( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_MISSING )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True )
        
        self.assertTrue( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetPaused( True )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetPaused( False )
        
        self.assertTrue( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_MISSING )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', is_dead = True )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
        #
        
        query_header = generate_fleshed_out_query_header( 'cool_stuff', with_outstanding_files = True, is_dead = True )
        
        self.assertTrue( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetPaused( True )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetPaused( False )
        
        self.assertTrue( query_header.IsExpectingToWorkInFuture() )
        
        query_header.SetQueryLogContainerStatus( ClientImportSubscriptionQuery.LOG_CONTAINER_MISSING )
        
        self.assertFalse( query_header.IsExpectingToWorkInFuture() )
        
    
