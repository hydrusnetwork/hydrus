from . import ClientConstants as CC
from . import ClientDefaults
from . import ClientImportSubscriptions
from . import ClientNetworking
from . import ClientNetworkingBandwidth
from . import ClientNetworkingDomain
from . import ClientNetworkingLogin
from . import ClientNetworkingSessions
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
        
        # wait until I have searcher in here, so I can roll it all into domain_manager etc... rather than hitting db for gallery init and all that
        
        # use safebooru (i.e. gelb 0.2.0) for examples. pseudo html documents here that work with the parsers
        
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
        
