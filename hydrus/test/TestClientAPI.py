import hashlib
import http.client
import json
import os
import random
import time
import typing
import unittest
import urllib
import urllib.parse

from unittest import mock

from twisted.internet import reactor

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPaths
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTags
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.files import HydrusFilesPhysicalStorage
from hydrus.core.files.images import HydrusImageHandling

from hydrus.client import ClientAPI
from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client import ClientLocation
from hydrus.client import ClientServices
from hydrus.client import ClientTime
from hydrus.client.duplicates import ClientDuplicates
from hydrus.client.duplicates import ClientPotentialDuplicatesSearchContext
from hydrus.client.importing import ClientImportFiles
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientContentUpdates
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientNetworkingContexts
from hydrus.client.networking.api import ClientLocalServer
from hydrus.client.networking.api import ClientLocalServerCore
from hydrus.client.search import ClientSearchFileSearchContext
from hydrus.client.search import ClientSearchPredicate
from hydrus.client.search import ClientSearchTagContext

from hydrus.test import HelperFunctions as HF
from hydrus.test import TestGlobals as TG

CBOR_AVAILABLE = False
try:
    import cbor2
    import base64
    CBOR_AVAILABLE = True
except:
    pass

def wash_example_json_response( obj ):
    
    if isinstance( obj, dict ):
        
        obj[ 'version' ] = HC.CLIENT_API_VERSION
        obj[ 'hydrus_version' ] = HC.SOFTWARE_VERSION
        
    

def GetExampleServicesDict():
    
    services_dict = {
        '6c6f63616c2074616773': {
            'name' : 'my tags',
            'type' : 5,
            'type_pretty' : 'local tag domain'
        },
        TG.test_controller.example_tag_repo_service_key.hex() : {
            'name' : 'example tag repo',
            'type' : 0,
            'type_pretty' : 'hydrus tag repository'
        },
        '6c6f63616c2066696c6573' : {
            'name' : 'my files',
            'type' : 2,
            'type_pretty' : 'local file domain'
        },
        '7265706f7369746f72792075706461746573' : {
            'name' : 'repository updates',
            'type' : 20,
            'type_pretty' : 'local update file domain'
        },
        TG.test_controller.example_file_repo_service_key_1.hex() : {
            'name' : 'example file repo 1',
            'type' : 1,
            'type_pretty' : 'hydrus file repository'
        },
        TG.test_controller.example_file_repo_service_key_2.hex() : {
            'name' : 'example file repo 2',
            'type' : 1,
            'type_pretty' : 'hydrus file repository'
        },
        '616c6c206c6f63616c2066696c6573' : {
            'name' : 'hydrus local file storage',
            'type' : 15,
            'type_pretty' : 'virtual combined local file domain'
        },
        '616c6c206c6f63616c206d65646961' : {
            'name' : 'combined local file domains',
            'type' : 21,
            'type_pretty' : 'virtual combined local media domain'
        },
        '616c6c206b6e6f776e2066696c6573' : {
            'name' : 'all known files',
            'type' : 11,
            'type_pretty' : 'virtual combined file domain'
        },
        '616c6c206b6e6f776e2074616773' : {
            'name' : 'all known tags',
            'type' : 10,
            'type_pretty' : 'virtual combined tag domain'
        },
        TG.test_controller.example_like_rating_service_key.hex() : {
            'name' : 'example local rating like service',
            'type' : 7,
            'type_pretty' : 'local like/dislike rating service',
            'star_shape' : 'svg'
        },
        TG.test_controller.example_numerical_rating_service_key.hex() : {
            'name' : 'example local rating numerical service',
            'type' : 6,
            'type_pretty' : 'local numerical rating service',
            'min_stars' : 0,
            'max_stars' : 5,
            'star_shape' : 'circle'
        },
        TG.test_controller.example_incdec_rating_service_key.hex() : {
            'name' : 'example local rating inc/dec service',
            'type' : 22,
            'type_pretty' : 'local inc/dec rating service'
        },
        '7472617368' : {
            'name' : 'trash',
            'type' : 14,
            'type_pretty' : 'local trash file domain'
        }
    }
    
    return services_dict
    

class TestClientAPI( unittest.TestCase ):
    
    _client_api: typing.Any = None
    _client_api_cors: typing.Any = None
    
    @classmethod
    def setUpClass( cls ):
        
        cls.maxDiff = None
        
        cls._client_api = ClientServices.GenerateService( CC.CLIENT_API_SERVICE_KEY, HC.CLIENT_API_SERVICE, 'client api' )
        cls._client_api_cors = ClientServices.GenerateService( CC.CLIENT_API_SERVICE_KEY, HC.CLIENT_API_SERVICE, 'client api' )
        
        cls._client_api_cors._support_cors = True
        
        def TWISTEDSetup():
            
            reactor.listenTCP( 45869, ClientLocalServer.HydrusServiceClientAPI( cls._client_api, allow_non_local_connections = False ) )
            reactor.listenTCP( 45899, ClientLocalServer.HydrusServiceClientAPI( cls._client_api_cors, allow_non_local_connections = False ) )
            
        
        reactor.callFromThread( TWISTEDSetup )
        
        time.sleep( 1 )
        
    
    def _test_basics( self, connection ):
        
        #
        
        connection.request( 'GET', '/' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        #
        
        with open( HydrusStaticDir.GetStaticPath( 'hydrus.ico' ), 'rb' ) as f:
            
            favicon = f.read()
            
        
        connection.request( 'GET', '/favicon.ico' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, favicon )
        
    
    def _test_cbor( self, connection, set_up_permissions ):
        
        # get url files
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        json_headers = dict( headers )
        json_headers[ 'Accept' ] = 'application/json'
        
        cbor_headers = dict( headers )
        cbor_headers[ 'Accept' ] = 'application/cbor'
        
        url = 'http://safebooru.org/index.php?page=post&s=view&id=2753608'
        normalised_url = 'https://safebooru.org/index.php?id=2753608&page=post&s=view'
        
        expected_result = {}
        
        expected_result[ 'request_url' ] = normalised_url
        expected_result[ 'normalised_url' ] = normalised_url
        expected_result[ 'url_type' ] = HC.URL_TYPE_POST
        expected_result[ 'url_type_string' ] = 'post url'
        expected_result[ 'match_name' ] = 'safebooru file page'
        expected_result[ 'can_parse' ] = True
        
        cbor_expected_result = dict( expected_result )
        
        wash_example_json_response( expected_result )
        
        hash = os.urandom( 32 )
        
        # normal GET json
        
        path = '/add_urls/get_url_info?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.headers[ 'Content-Type' ], 'application/json' )
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_result )
        
        # explicit GET cbor by arg
        
        path = '/add_urls/get_url_info?url={}&cbor=1'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.headers[ 'Content-Type' ], 'application/cbor' )
        self.assertEqual( response.status, 200 )
        
        d = cbor2.loads( data )
        
        self.assertEqual( d, cbor_expected_result )
        
        # explicit GET json by Accept
        
        path = '/add_urls/get_url_info?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = json_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.headers[ 'Content-Type' ], 'application/json' )
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_result )
        
        # explicit GET cbor by Accept
        
        path = '/add_urls/get_url_info?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = cbor_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.headers[ 'Content-Type' ], 'application/cbor' )
        self.assertEqual( response.status, 200 )
        
        d = cbor2.loads( data )
        
        self.assertEqual( d, cbor_expected_result )
        
    
    def _test_client_api_basics( self, connection ):
        
        # /api_version
        
        connection.request( 'GET', '/api_version' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'version' ], HC.CLIENT_API_VERSION )
        self.assertEqual( response_json[ 'hydrus_version' ], HC.SOFTWARE_VERSION )
        
        # /request_new_permissions
        
        def format_request_new_permissions_query( name, permits_everything, basic_permissions ):
            
            if permits_everything:
                
                return f'/request_new_permissions?name={urllib.parse.quote( name )}&permits_everything=true'
                
            else:
                
                return f'/request_new_permissions?name={urllib.parse.quote( name )}&basic_permissions={urllib.parse.quote( json.dumps( basic_permissions ) )}'
                
            
        
        # fail as dialog not open
        
        ClientAPI.api_request_dialog_open = False
        
        connection.request( 'GET', format_request_new_permissions_query( 'test', False, [ ClientAPI.CLIENT_API_PERMISSION_ADD_FILES ] ) )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 409 )
        
        self.assertIn( 'dialog', text )
        
        # success
        
        permissions_to_set_up = []
        
        permissions_to_set_up.append( ( 'everything', True, [] ) )
        permissions_to_set_up.append( ( 'add_files', False, [ ClientAPI.CLIENT_API_PERMISSION_ADD_FILES ] ) )
        permissions_to_set_up.append( ( 'add_tags', False, [ ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS ] ) )
        permissions_to_set_up.append( ( 'add_urls', False, [ ClientAPI.CLIENT_API_PERMISSION_ADD_URLS ] ) )
        permissions_to_set_up.append( ( 'manage_pages', False, [ ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES ] ) )
        permissions_to_set_up.append( ( 'manage_headers', False, [ ClientAPI.CLIENT_API_PERMISSION_MANAGE_HEADERS ] ) )
        permissions_to_set_up.append( ( 'search_all_files', False, [ ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES ] ) )
        permissions_to_set_up.append( ( 'search_green_files', False, [ ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES ] ) )
        
        set_up_permissions = {}
        
        for ( name, permits_everything, basic_permissions ) in permissions_to_set_up:
            
            ClientAPI.api_request_dialog_open = True
            
            connection.request( 'GET', format_request_new_permissions_query( name, permits_everything, basic_permissions ) )
            
            response = connection.getresponse()
            
            data = response.read()
            
            ClientAPI.api_request_dialog_open = False
            
            response_text = str( data, 'utf-8' )
            
            self.assertEqual( response.status, 200 )
            
            response_json = json.loads( response_text )
            
            access_key_hex = response_json[ 'access_key' ]
            
            self.assertEqual( len( access_key_hex ), 64 )
            
            access_key_hex = HydrusText.HexFilter( access_key_hex )
            
            self.assertEqual( len( access_key_hex ), 64 )
            
            api_permissions = ClientAPI.last_api_permissions_request
            
            if 'green' in name:
                
                search_tag_filter = HydrusTags.TagFilter()
                
                search_tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
                search_tag_filter.SetRule( ' :', HC.FILTER_BLACKLIST )
                search_tag_filter.SetRule( 'green', HC.FILTER_WHITELIST )
                
                api_permissions.SetSearchTagFilter( search_tag_filter )
                
            
            if 'everything' in name:
                
                self.assertTrue( api_permissions.PermitsEverything() )
                
            else:
                
                self.assertFalse( api_permissions.PermitsEverything() )
                
            
            self.assertEqual( bytes.fromhex( access_key_hex ), api_permissions.GetAccessKey() )
            
            set_up_permissions[ name ] = api_permissions
            
            TG.test_controller.client_api_manager.AddAccess( api_permissions )
            
        
        # /verify_access_key
        
        # missing
        
        connection.request( 'GET', '/verify_access_key' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 401 )
        
        # fail header
        
        incorrect_headers = { 'Hydrus-Client-API-Access-Key' : 'abcd' }
        
        connection.request( 'GET', '/verify_access_key', headers = incorrect_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # fail get param
        
        connection.request( 'GET', '/verify_access_key?Hydrus-Client-API-Access-Key=abcd' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # success
        
        def do_good_verify_test( api_permissions, key_hex, key_name ):
            
            for request_type in ( 'header', 'get' ):
                
                if request_type == 'header' :
                    
                    headers = { key_name : key_hex }
                    
                    connection.request( 'GET', '/verify_access_key', headers = headers )
                    
                elif request_type == 'get' :
                    
                    connection.request( 'GET', '/verify_access_key?{}={}'.format( key_name, key_hex ) )
                    
                
                response = connection.getresponse()
                
                data = response.read()
                
                text = str( data, 'utf-8' )
                
                self.assertEqual( response.status, 200 )
                
                body_dict = json.loads( text )
                
                self.assertEqual( body_dict[ 'name' ], api_permissions.GetName() )
                self.assertEqual( body_dict[ 'permits_everything' ], api_permissions.PermitsEverything() )
                
                if api_permissions.PermitsEverything():
                    
                    self.assertEqual( set( body_dict[ 'basic_permissions' ] ), set( ClientAPI.ALLOWED_PERMISSIONS ) )
                    
                else:
                    
                    self.assertEqual( set( body_dict[ 'basic_permissions' ] ), set( api_permissions.GetBasicPermissions() ) )
                    
                
                self.assertEqual( body_dict[ 'human_description' ], api_permissions.ToHumanString() )
                
            
        
        for api_permissions in set_up_permissions.values():
            
            access_key_hex = api_permissions.GetAccessKey().hex()
            
            do_good_verify_test( api_permissions, access_key_hex, 'Hydrus-Client-API-Access-Key' )
            
        
        # /session_key
        
        # fail header
        
        incorrect_headers = { 'Hydrus-Client-API-Session-Key' : 'abcd' }
        
        connection.request( 'GET', '/verify_access_key', headers = incorrect_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 419 )
        
        # fail get param
        
        connection.request( 'GET', '/verify_access_key?Hydrus-Client-API-Session-Key=abcd' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 419 )
        
        # success
        
        for api_permissions in set_up_permissions.values():
            
            access_key_hex = api_permissions.GetAccessKey().hex()
            
            headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
            
            connection.request( 'GET', '/session_key', headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            text = str( data, 'utf-8' )
            
            body_dict = json.loads( text )
            
            self.assertEqual( response.status, 200 )
            
            self.assertIn( 'session_key', body_dict )
            
            session_key_hex = body_dict[ 'session_key' ]
            
            self.assertEqual( len( session_key_hex ), 64 )
            
            do_good_verify_test( api_permissions, session_key_hex, 'Hydrus-Client-API-Session-Key' )
            
        
        # test access in POST params
        
        # fail
        
        headers = { 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'Hydrus-Client-API-Access-Key' : 'abcd', 'hash' : hash_hex, 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : 'abcd', 'hash' : hash_hex, 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 419 )
        
        # success
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        connection.request( 'GET', '/session_key', headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        body_dict = json.loads( text )
        
        session_key_hex = body_dict[ 'session_key' ]
        
        headers = { 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'hash' : hash_hex, 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : session_key_hex, 'hash' : hash_hex, 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        self.assertTrue( content_update_package.HasContentForServiceKey( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ) )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : session_key_hex, 'hash' : hash_hex, 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        self.assertTrue( content_update_package.HasContentForServiceKey( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ) )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : session_key_hex, 'hash' : hash_hex, 'service_keys_to_actions_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : { str( HC.CONTENT_UPDATE_ADD ) : [ 'test', 'test2' ] } } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        self.assertTrue( content_update_package.HasContentForServiceKey( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ) )
        
        #
        
        return set_up_permissions
        
    
    def _test_cors_fails( self, connection ):
        
        connection.request( 'OPTIONS', '/api_version' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( response.getheader( 'Allow' ), 'GET' )
        
        #
        
        connection.request( 'OPTIONS', '/api_version', headers = { 'Origin' : 'muhsite.com' } )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 401 )
        
    
    def _test_cors_succeeds( self, connection ):
        
        connection.request( 'OPTIONS', '/api_version' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( response.getheader( 'Allow' ), 'GET' )
        
        #
        
        connection.request( 'OPTIONS', '/api_version', headers = { 'Origin' : 'muhsite.com' } )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( response.getheader( 'Access-Control-Allow-Methods' ), 'GET' )
        self.assertEqual( response.getheader( 'Access-Control-Allow-Headers' ), '*' )
        self.assertEqual( response.getheader( 'Access-Control-Allow-Origin' ), '*' )
        
    
    def _test_get_services( self, connection, set_up_permissions ):
        
        should_work = { set_up_permissions[ 'everything' ], set_up_permissions[ 'add_files' ], set_up_permissions[ 'add_tags' ], set_up_permissions[ 'manage_pages' ], set_up_permissions[ 'search_all_files' ], set_up_permissions[ 'search_green_files' ] }
        should_break = { set_up_permissions[ 'add_urls' ], set_up_permissions[ 'manage_headers' ] }
        
        expected_result = {
            'local_tags' : [
                {
                    'name' : 'my tags',
                    'service_key' : '6c6f63616c2074616773',
                    'type': 5,
                    'type_pretty': 'local tag domain'
                }
            ],
            'tag_repositories' : [
                {
                    'name' : 'example tag repo',
                    'service_key' : TG.test_controller.example_tag_repo_service_key.hex(),
                    'type': 0,
                    'type_pretty': 'hydrus tag repository'
                }
            ],
            'local_files' : [
                {
                    'name' : 'my files',
                    'service_key' : '6c6f63616c2066696c6573',
                    'type': 2,
                    'type_pretty': 'local file domain'
                }
            ],
            'local_updates' : [
                {
                    'name' : 'repository updates',
                    'service_key' : '7265706f7369746f72792075706461746573',
                    'type': 20,
                    'type_pretty': 'local update file domain'
                }
            ],
            'file_repositories' : [
                {
                    'name': 'example file repo 1',
                    'service_key': TG.test_controller.example_file_repo_service_key_1.hex(),
                    'type': 1,
                    'type_pretty': 'hydrus file repository'},
                {
                    'name': 'example file repo 2',
                    'service_key': TG.test_controller.example_file_repo_service_key_2.hex(),
                    'type': 1,
                    'type_pretty': 'hydrus file repository'
                }
            ],
            'all_local_files' : [
                {
                    'name' : 'hydrus local file storage',
                    'service_key' : '616c6c206c6f63616c2066696c6573',
                    'type' : 15,
                    'type_pretty' : 'virtual combined local file domain'
                }
            ],
            'all_local_media' : [
                {
                    'name' : 'combined local file domains',
                    'service_key' : '616c6c206c6f63616c206d65646961',
                    'type': 21,
                    'type_pretty': 'virtual combined local media domain'
                }
            ],
            'all_known_files' : [
                {
                    'name' : 'all known files',
                    'service_key' : '616c6c206b6e6f776e2066696c6573',
                    'type' : 11,
                    'type_pretty' : 'virtual combined file domain'
                }
            ],
            'all_known_tags' : [
                {
                    'name' : 'all known tags',
                    'service_key' : '616c6c206b6e6f776e2074616773',
                    'type' : 10,
                    'type_pretty' : 'virtual combined tag domain'
                }
            ],
            'trash' : [
                {
                    'name' : 'trash',
                    'service_key' : '7472617368',
                    'type': 14,
                    'type_pretty': 'local trash file domain'
                }
            ],
            'services' : GetExampleServicesDict()
        }
        
        wash_example_json_response( expected_result )
        
        get_service_expected_result = {
            'service' : {
                'name' : 'repository updates',
                'service_key' : '7265706f7369746f72792075706461746573',
                'type': 20,
                'type_pretty': 'local update file domain'
            }
        }
        
        wash_example_json_response( get_service_expected_result )
        
        for api_permissions in should_work.union( should_break ):
            
            access_key_hex = api_permissions.GetAccessKey().hex()
            
            headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
            
            #
            
            path = '/get_services'
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            if api_permissions in should_work:
                
                text = str( data, 'utf-8' )
                
                self.assertEqual( response.status, 200 )
                
                d = json.loads( text )
                
                self.assertEqual( d, expected_result )
                
            else:
                
                self.assertEqual( response.status, 403 )
                
            
            #
            
            path = '/get_service?service_name=repository%20updates'
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            if api_permissions in should_work:
                
                text = str( data, 'utf-8' )
                
                self.assertEqual( response.status, 200 )
                
                d = json.loads( text )
                
                self.assertEqual( d, get_service_expected_result )
                
            else:
                
                self.assertEqual( response.status, 403 )
                
            
            path = '/get_service?service_key={}'.format( CC.LOCAL_UPDATE_SERVICE_KEY.hex() )
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            if api_permissions in should_work:
                
                text = str( data, 'utf-8' )
                
                self.assertEqual( response.status, 200 )
                
                d = json.loads( text )
                
                self.assertEqual( d, get_service_expected_result )
                
            else:
                
                self.assertEqual( response.status, 403 )
                
            
            
        
    
    def _test_get_service_svg( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'add_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = f'/get_service_rating_svg?service_key={TG.test_controller.example_like_rating_service_key.hex()}'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.getheader( 'content-type' ), 'image/svg+xml' )
        
        svg_path = HydrusStaticDir.GetSVGPath( 'star' )
        
        svg_file = open( svg_path, 'rb' )
        
        svg_content = svg_file.read()
        
        self.assertEqual( data, svg_content )
        
    
    def _test_add_files_add_file( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'add_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        # fail
        
        hash = bytes.fromhex( 'a593942cb7ea9ffcd8ccf2f0fa23c338e23bfecd9a3e508dfc0bcf07501ead08' )
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        
        TG.test_controller.SetRead( 'hash_status', f )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_OCTET_STREAM ] }
        
        path = '/add_files/add_file'
        
        body = b'blarg'
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'status' ], CC.STATUS_ERROR )
        self.assertEqual( response_json[ 'hash' ], hash.hex() )
        self.assertIn( 'Unknown', response_json[ 'note' ] )
        self.assertIn( 'Traceback', response_json[ 'traceback' ] )
        
        # success as body
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        f.note = 'test note'
        
        TG.test_controller.SetRead( 'hash_status', f )
        
        hydrus_png_path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        with open( hydrus_png_path, 'rb' ) as f:
            
            HYDRUS_PNG_BYTES = f.read()
            
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_OCTET_STREAM ] }
        
        path = '/add_files/add_file'
        
        body = HYDRUS_PNG_BYTES
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        expected_result = { 'status' : CC.STATUS_SUCCESSFUL_AND_NEW, 'hash' : hash.hex() , 'note' : 'test note' }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( response_json, expected_result )
        
        # do hydrus png as path
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        f.note = 'test note'
        
        TG.test_controller.SetRead( 'hash_status', f )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/add_files/add_file'
        
        body_dict = { 'path' : hydrus_png_path }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        expected_result = { 'status' : CC.STATUS_SUCCESSFUL_AND_NEW, 'hash' : hash.hex() , 'note' : 'test note' }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( response_json, expected_result )
        
        self.assertTrue( os.path.exists( hydrus_png_path ) )
        
        # do hydrus png as path, and delete it
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        f.note = 'test note'
        
        TG.test_controller.SetRead( 'hash_status', f )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/add_files/add_file'
        
        temp_hydrus_png_path = os.path.join( TG.test_controller.db_dir, 'hydrus_png_client_api_import_test.wew' )
        
        HydrusPaths.MirrorFile( hydrus_png_path, temp_hydrus_png_path )
        
        body_dict = { 'path' : temp_hydrus_png_path, 'delete_after_successful_import' : True }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        expected_result = { 'status' : CC.STATUS_SUCCESSFUL_AND_NEW, 'hash' : hash.hex() , 'note' : 'test note' }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( response_json, expected_result )
        
        self.assertFalse( os.path.exists( temp_hydrus_png_path ) )
        
    
    def _test_add_files_migrate_files( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'add_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        #
        
        hash = HydrusData.GenerateKey()
        
        # missing file
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/migrate_files'
        
        body_dict = { 'hash' : hash.hex(), 'file_service_key' : CC.LOCAL_FILE_SERVICE_KEY.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 ) # file not in local domain
        
        # already-in no-op
        
        magic_now = 150
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = magic_now ):
            
            hash = HydrusData.GenerateKey()
            
            media_result = HF.GetFakeMediaResult( hash )
            
            media_result.GetLocationsManager()._current = { CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY }
            media_result.GetLocationsManager()._service_keys_to_filenames = {
                CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY : 100,
                CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY : 100,
                CC.LOCAL_FILE_SERVICE_KEY : 100
            }
            
            TG.test_controller.ClearWrites( 'content_updates' )
            
            TG.test_controller.SetRead( 'media_results', [ media_result ] )
            
            #
            
            path = '/add_files/migrate_files'
            
            body_dict = { 'hash' : hash.hex(), 'file_service_key' : CC.LOCAL_FILE_SERVICE_KEY.hex() }
            
            body = json.dumps( body_dict )
            
            connection.request( 'POST', path, body = body, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            self.assertEqual( response.status, 200 )
            
            results = TG.test_controller.GetWrite( 'content_updates' )
            
            self.assertEqual( results, [] )
            
        
        # normal copy
        
        magic_now = 150
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = magic_now ):
            
            hash = HydrusData.GenerateKey()
            
            media_result = HF.GetFakeMediaResult( hash )
            
            some_file_service_key = HydrusData.GenerateKey()
            
            media_result.GetLocationsManager()._current = { CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, some_file_service_key }
            media_result.GetLocationsManager()._service_keys_to_filenames = {
                CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY : 100,
                CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY : 100,
                some_file_service_key : 100
            }
            
            TG.test_controller.ClearWrites( 'content_updates' )
            
            TG.test_controller.SetRead( 'media_results', [ media_result ] )
            
            #
            
            path = '/add_files/migrate_files'
            
            body_dict = { 'hash' : hash.hex(), 'file_service_key' : CC.LOCAL_FILE_SERVICE_KEY.hex() }
            
            body = json.dumps( body_dict )
            
            connection.request( 'POST', path, body = body, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            self.assertEqual( response.status, 200 )
            
            time.sleep( 0.25 )
            
            [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
            
            expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_FILE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ADD, ( media_result.GetFileInfoManager(), magic_now ) ) ] )
            
            HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
            
        
    
    def _test_add_files_other_actions( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'add_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        #
        
        file_id = random.randint( 10000, 15000 )
        
        hash = HydrusData.GenerateKey()
        hashes = { HydrusData.GenerateKey() for i in range( 10 ) }
        
        file_ids_to_hashes = { file_id : hash for ( file_id, hash ) in zip( random.sample( range( 2000 ), 10 ), hashes ) }
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/delete_files'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { hash }, reason = 'Deleted via Client API.' ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # with file_id
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { file_id : hash } )
        
        path = '/add_files/delete_files'
        
        body_dict = { 'file_id' : file_id }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { hash }, reason = 'Deleted via Client API.' ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        TG.test_controller.ClearReads( 'hash_ids_to_hashes' )
        
        # with hashes
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/delete_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ] }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes, reason = 'Deleted via Client API.' ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # with file_ids
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', file_ids_to_hashes )
        
        path = '/add_files/delete_files'
        
        body_dict = { 'file_ids' : list( file_ids_to_hashes.keys() ) }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes, reason = 'Deleted via Client API.' ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        TG.test_controller.ClearReads( 'hash_ids_to_hashes' )
        
        # now with a reason
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/delete_files'
        
        reason = 'yo'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ], 'reason' : reason }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes, reason = reason ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # now test it not working
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/delete_files'
        
        not_existing_service_hex = os.urandom( 32 ).hex()
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ], 'file_service_key' : not_existing_service_hex }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 )
        
        text = str( data, 'utf-8' )
        
        self.assertIn( not_existing_service_hex, text ) # error message should be complaining about it
        
        # test file lock, 200 response
        
        locked_hash = list( hashes )[0]
        
        media_result = HF.GetFakeMediaResult( locked_hash )
        
        media_result.GetLocationsManager().inbox = False
        
        TG.test_controller.new_options.SetBoolean( 'delete_lock_for_archived_files', True )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        TG.test_controller.SetRead( 'media_results', [ media_result ] )
        
        path = '/add_files/delete_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ], 'file_service_key' : CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        CG.client_controller.new_options.SetBoolean( 'delete_lock_for_archived_files', False )
        
        TG.test_controller.ClearReads( 'media_results' )
        
        # test file lock, 409 response
        
        locked_hash = list( hashes )[0]
        
        media_result = HF.GetFakeMediaResult( locked_hash )
        
        media_result.GetLocationsManager().inbox = False
        
        TG.test_controller.new_options.SetBoolean( 'delete_lock_for_archived_files', True )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        TG.test_controller.SetRead( 'media_results', [ media_result ] )
        
        path = '/add_files/delete_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ], 'file_service_key' : CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 409 )
        
        text = str( data, 'utf-8' )
        
        self.assertIn( locked_hash.hex(), text ) # error message should be complaining about it
        
        CG.client_controller.new_options.SetBoolean( 'delete_lock_for_archived_files', False )
        
        TG.test_controller.ClearReads( 'media_results' )
        
        #
        
        media_result = HF.GetFakeMediaResult( hash )
        
        TG.test_controller.SetRead( 'media_results', [ media_result ] )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/undelete_files'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, { hash } ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        media_results = [ HF.GetFakeMediaResult( h ) for h in hashes ]
        
        TG.test_controller.SetRead( 'media_results', media_results )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/undelete_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ] }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, hashes ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/undelete_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ], 'file_service_key' : not_existing_service_hex }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 )
        
        text = str( data, 'utf-8' )
        
        self.assertIn( not_existing_service_hex, text ) # error message should be complaining about it
        
        #
        
        media_result = HF.GetFakeMediaResult( hash )
        
        
        deleted_timestamp_ms = 5000000
        previously_imported_timestamp_ms = 2500000
        
        deleted_to_timestamps_ms = { CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY : deleted_timestamp_ms, CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY : deleted_timestamp_ms, CC.LOCAL_FILE_SERVICE_KEY : deleted_timestamp_ms }
        deleted_to_previously_imported_timestamp_ms = { CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY : previously_imported_timestamp_ms, CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY : previously_imported_timestamp_ms, CC.LOCAL_FILE_SERVICE_KEY : previously_imported_timestamp_ms }
        
        times_manager = ClientMediaManagers.TimesManager()
        
        times_manager.SetDeletedTimestampsMS( deleted_to_timestamps_ms )
        times_manager.SetPreviouslyImportedTimestampsMS( deleted_to_previously_imported_timestamp_ms )
        
        locations_manager = ClientMediaManagers.LocationsManager(
            set(),
            set( deleted_to_timestamps_ms.keys() ),
            set(),
            set(),
            times_manager,
            inbox = False,
            urls = set(),
            service_keys_to_filenames = {}
        )
        
        media_result._locations_manager = locations_manager
        
        TG.test_controller.SetRead( 'media_results', [ media_result ] )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/clear_file_deletion_record'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_CLEAR_DELETE_RECORD, { hash } ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/archive_files'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, { hash } ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/archive_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ] }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/unarchive_files'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, { hash } ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/unarchive_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ] }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes ) ] )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
    
    def _test_add_files_generate_hashes( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'add_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        # as body
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        
        hydrus_png_path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        with open( hydrus_png_path, 'rb' ) as f:
            
            HYDRUS_PNG_BYTES = f.read()
            
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_OCTET_STREAM ] }
        
        path = '/add_files/generate_hashes'
        
        body = HYDRUS_PNG_BYTES
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        expected_result = { 'hash' : hash.hex(), 'perceptual_hashes' : ["b44dc7b24dcb381c"] , 'pixel_hash' : 'e12db22bf8ecf1f54ae1df3f0675a34a64e0c8f0801ae816b8aaae00f5d7f4fc' }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( response_json, expected_result )
        
        # do hydrus png as path
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        
        hydrus_png_path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/add_files/generate_hashes'
        
        body_dict = { 'path' : hydrus_png_path }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        expected_result = { 'hash' : hash.hex(), 'perceptual_hashes' : ["b44dc7b24dcb381c"] , 'pixel_hash' : 'e12db22bf8ecf1f54ae1df3f0675a34a64e0c8f0801ae816b8aaae00f5d7f4fc' }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( response_json, expected_result )
        
    
    def _test_add_notes( self, connection, set_up_permissions ):
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        # set notes
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_notes/set_notes'
        
        new_notes_dict = { 'new note' : 'hello test', 'new note 2' : 'hello test 2' }
        
        body_dict = { 'hash' : hash_hex, 'notes' : new_notes_dict }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'notes' ], new_notes_dict )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, name, note ) ) for ( name, note ) in new_notes_dict.items() ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # delete notes
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_notes/delete_notes'
        
        delete_note_names = { 'new note 3', 'new note 4' }
        
        body_dict = { 'hash' : hash_hex, 'note_names' : list( delete_note_names ) }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_DELETE, ( hash, name ) ) for name in delete_note_names ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set notes with merge
        
        # setup
        
        file_id = 1
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        hash_hex = hash.hex()
        
        size = 100
        mime = HC.IMAGE_PNG
        width = 20
        height = 20
        duration_ms = None
        
        file_info_manager = ClientMediaManagers.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration_ms = duration_ms )
        
        service_keys_to_statuses_to_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'blue_eyes', 'blonde_hair' }, HC.CONTENT_STATUS_PENDING : { 'bodysuit' } } }
        service_keys_to_statuses_to_display_tags =  { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : { 'blue eyes', 'blonde hair' }, HC.CONTENT_STATUS_PENDING : { 'bodysuit', 'clothing' } } }
        
        tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
        
        times_manager = ClientMediaManagers.TimesManager()
        
        locations_manager = ClientMediaManagers.LocationsManager( set(), set(), set(), set(), times_manager )
        ratings_manager = ClientMediaManagers.RatingsManager( {} )
        notes_manager = ClientMediaManagers.NotesManager( { 'abc' : '123' } )
        file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager( times_manager )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
        from hydrus.client.importing.options import NoteImportOptions
        
        # extend
        
        TG.test_controller.SetRead( 'media_result', media_result )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_notes/set_notes'
        
        new_notes_dict = { 'abc' : '1234' }
        
        body_dict = { 'hash' : hash_hex, 'notes' : new_notes_dict, 'merge_cleverly' : True, 'extend_existing_note_if_possible' : True, 'conflict_resolution' : NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'notes' ], new_notes_dict )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, 'abc', '1234' ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # no extend (rename)
        
        TG.test_controller.SetRead( 'media_result', media_result )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_notes/set_notes'
        
        new_notes_dict = { 'abc' : '1234' }
        
        body_dict = { 'hash' : hash_hex, 'notes' : new_notes_dict, 'merge_cleverly' : True, 'extend_existing_note_if_possible' : False, 'conflict_resolution' : NoteImportOptions.NOTE_IMPORT_CONFLICT_RENAME }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'notes' ], { 'abc (1)' : '1234' } )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, 'abc (1)', '1234' ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # ignore
        
        TG.test_controller.SetRead( 'media_result', media_result )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_notes/set_notes'
        
        new_notes_dict = { 'abc' : '789' }
        
        body_dict = { 'hash' : hash_hex, 'notes' : new_notes_dict, 'merge_cleverly' : True, 'extend_existing_note_if_possible' : True, 'conflict_resolution' : NoteImportOptions.NOTE_IMPORT_CONFLICT_IGNORE }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'notes' ], {} )
        
        stuff = TG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( stuff, [] )
        
        # append
        
        TG.test_controller.SetRead( 'media_result', media_result )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_notes/set_notes'
        
        new_notes_dict = { 'abc' : '789' }
        
        body_dict = { 'hash' : hash_hex, 'notes' : new_notes_dict, 'merge_cleverly' : True, 'extend_existing_note_if_possible' : True, 'conflict_resolution' : NoteImportOptions.NOTE_IMPORT_CONFLICT_APPEND }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'notes' ], { 'abc' : '123\n\n789' } )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, 'abc', '123\n\n789' ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # replace
        
        TG.test_controller.SetRead( 'media_result', media_result )
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_notes/set_notes'
        
        new_notes_dict = { 'abc' : '789' }
        
        body_dict = { 'hash' : hash_hex, 'notes' : new_notes_dict, 'merge_cleverly' : True, 'extend_existing_note_if_possible' : True, 'conflict_resolution' : NoteImportOptions.NOTE_IMPORT_CONFLICT_REPLACE }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'notes' ], { 'abc' : '789' } )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.LOCAL_NOTES_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_NOTES, HC.CONTENT_UPDATE_SET, ( hash, 'abc', '789' ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
    
    def _test_edit_file_viewing_statistics( self, connection, set_up_permissions ):
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        # increment
        
        jobs = []
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'viewtime' : 3.800
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        jobs.append( ( request_args, media_result, CC.CANVAS_MEDIA_VIEWER, None, 1, 3800 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_PREVIEW,
            'views' : 3,
            'viewtime' : 3.900
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        jobs.append( ( request_args, media_result, CC.CANVAS_PREVIEW, None, 3, 3900 ) )
        
        #
        
        timestamp_ms = HydrusTime.GetNowMS() - 50000
        
        request_args = {
            'canvas_type' : CC.CANVAS_CLIENT_API,
            'timestamp_ms' : timestamp_ms,
            'viewtime' : 3.950
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        jobs.append( ( request_args, media_result, CC.CANVAS_CLIENT_API, timestamp_ms, 1, 3950 ) )
        
        #
        
        magic_now = 123456789
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = magic_now ):
            
            for ( request_args, media_result, canvas_type, new_timestamp_ms, new_views, new_viewtime ) in jobs:
                
                media_result = typing.cast( ClientMediaResult.MediaResult, media_result )
                
                TG.test_controller.ClearWrites( 'content_updates' )
                
                path = '/edit_times/increment_file_viewtime'
                
                body_dict = { 'hash' : hash_hex }
                body_dict.update( request_args )
                
                body = json.dumps( body_dict )
                
                connection.request( 'POST', path, body = body, headers = headers )
                
                response = connection.getresponse()
                
                data = response.read()
                
                self.assertEqual( response.status, 200 )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage()
                
                timestamp_we_expect = magic_now if new_timestamp_ms is None else new_timestamp_ms
                
                content_update_row = ( hash, canvas_type, timestamp_we_expect, new_views, new_viewtime )
                
                expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates(
                    CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY,
                    [
                        ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_ADD, content_update_row )
                    ]
                )
                
                [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
                
                HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
                
            
        
        #
        
        problem_jobs = []
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'viewtime' : 123456
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER_ARCHIVE_DELETE,
            'viewtime' : 123456
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'viewtime' : -123456
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'views' : -5,
            'viewtime' : 123456
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        for ( request_args, expected_status ) in problem_jobs:
            
            media_result = HF.GetFakeMediaResult( hash )
            
            TG.test_controller.SetRead( 'media_results', [ media_result ] )
            
            TG.test_controller.ClearWrites( 'content_updates' )
            
            path = '/edit_times/increment_file_viewtime'
            
            body_dict = { 'hash' : hash_hex }
            body_dict.update( request_args )
            
            body = json.dumps( body_dict )
            
            connection.request( 'POST', path, body = body, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            self.assertEqual( response.status, expected_status )
            
        
        # set
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        # set up jobs
        
        jobs = []
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'views' : 1,
            'viewtime' : 3.800
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        jobs.append( ( request_args, media_result, CC.CANVAS_MEDIA_VIEWER, None, 1, 3800 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_PREVIEW,
            'views' : 3,
            'viewtime' : 3.900
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        jobs.append( ( request_args, media_result, CC.CANVAS_PREVIEW, None, 3, 3900 ) )
        
        #
        
        timestamp_ms = HydrusTime.GetNowMS() - 50000
        
        request_args = {
            'canvas_type' : CC.CANVAS_CLIENT_API,
            'timestamp_ms' : timestamp_ms,
            'views' : 16,
            'viewtime' : 13.950
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        jobs.append( ( request_args, media_result, CC.CANVAS_CLIENT_API, timestamp_ms, 16, 13950 ) )
        
        #
        
        magic_now = 123456789
        
        with mock.patch.object( HydrusTime, 'GetNowMS', return_value = magic_now ):
            
            for ( request_args, media_result, canvas_type, new_timestamp_ms, new_views, new_viewtime ) in jobs:
                
                media_result = typing.cast( ClientMediaResult.MediaResult, media_result )
                
                TG.test_controller.ClearWrites( 'content_updates' )
                
                path = '/edit_times/set_file_viewtime'
                
                body_dict = { 'hash' : hash_hex }
                body_dict.update( request_args )
                
                body = json.dumps( body_dict )
                
                connection.request( 'POST', path, body = body, headers = headers )
                
                response = connection.getresponse()
                
                data = response.read()
                
                self.assertEqual( response.status, 200 )
                
                content_update_package = ClientContentUpdates.ContentUpdatePackage()
                
                # if not set, new_timestamp_ms will be None
                content_update_row = ( hash, canvas_type, new_timestamp_ms, new_views, new_viewtime )
                
                expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates(
                    CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY,
                    [
                        ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILE_VIEWING_STATS, HC.CONTENT_UPDATE_SET, content_update_row )
                    ]
                )
                
                [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
                
                HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
                
            
        
        #
        
        problem_jobs = []
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'views' : 1
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'viewtime' : 123456,
            'views' : 1
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'viewtime' : 123456
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER_ARCHIVE_DELETE,
            'views' : 1,
            'viewtime' : 123456
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'views' : -1,
            'viewtime' : 123456
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'views' : 1,
            'viewtime' : -123456
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        for ( request_args, expected_status ) in problem_jobs:
            
            media_result = HF.GetFakeMediaResult( hash )
            
            TG.test_controller.SetRead( 'media_results', [ media_result ] )
            
            TG.test_controller.ClearWrites( 'content_updates' )
            
            path = '/edit_times/set_file_viewtime'
            
            body_dict = { 'hash' : hash_hex }
            body_dict.update( request_args )
            
            body = json.dumps( body_dict )
            
            connection.request( 'POST', path, body = body, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            self.assertEqual( response.status, expected_status )
            
        
    
    def _test_edit_ratings( self, connection, set_up_permissions ):
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        # set like like
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_like_rating_service_key.hex(), 'rating' : True }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_like_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set like dislike
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_like_rating_service_key.hex(), 'rating' : False }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_like_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.0, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set like None
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_like_rating_service_key.hex(), 'rating' : None }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_like_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set numerical 0
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_numerical_rating_service_key.hex(), 'rating' : 0 }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_numerical_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.0, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set numerical 2 (0.4)
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_numerical_rating_service_key.hex(), 'rating' : 2 }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_numerical_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0.4, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set numerical 5 (1.0)
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_numerical_rating_service_key.hex(), 'rating' : 5 }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_numerical_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 1.0, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set numerical None
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_numerical_rating_service_key.hex(), 'rating' : None }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_numerical_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( None, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set incdec 0
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_incdec_rating_service_key.hex(), 'rating' : 0 }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_incdec_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set incdec 5
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_incdec_rating_service_key.hex(), 'rating' : 5 }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_incdec_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 5, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # set incdec -3
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/edit_ratings/set_rating'
        
        body_dict = { 'hash' : hash_hex, 'rating_service_key' : TG.test_controller.example_incdec_rating_service_key.hex(), 'rating' : -3 }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_incdec_rating_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_RATINGS, HC.CONTENT_UPDATE_ADD, ( 0, { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
    
    def _test_edit_times( self, connection, set_up_permissions ):
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        # set up jobs
        
        jobs = []
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_ARCHIVED,
            'timestamp' : 123456
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetArchivedTimestampMS( HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_ARCHIVED, timestamp_ms = 123456000 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_ARCHIVED,
            'timestamp' : 123456.789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetArchivedTimestampMS( HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_ARCHIVED, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_ARCHIVED,
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetArchivedTimestampMS( HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_ARCHIVED, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        # all timestamp params are now tested and good. let's now hit the different types
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_MODIFIED_FILE,
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetFileModifiedTimestampMS( HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_MODIFIED_FILE, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN,
            'domain' : 'local',
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetFileModifiedTimestampMS( HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_MODIFIED_FILE, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN,
            'domain' : 'site.com',
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetDomainModifiedTimestampMS( 'site.com', HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN, location = 'site.com', timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_LAST_VIEWED,
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER,
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER, HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_LAST_VIEWED, location = CC.CANVAS_MEDIA_VIEWER, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_LAST_VIEWED,
            'canvas_type' : CC.CANVAS_PREVIEW,
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetLastViewedTimestampMS( CC.CANVAS_PREVIEW, HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_LAST_VIEWED, location = CC.CANVAS_PREVIEW, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_LAST_VIEWED,
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetLastViewedTimestampMS( CC.CANVAS_MEDIA_VIEWER, HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_LAST_VIEWED, location = CC.CANVAS_MEDIA_VIEWER, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_IMPORTED,
            'file_service_key' : CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY.hex(),
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetImportedTimestampMS( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_IMPORTED, location = CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_DELETED,
            'file_service_key' : CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY.hex(),
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetDeletedTimestampMS( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_DELETED, location = CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED,
            'file_service_key' : CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY.hex(),
            'timestamp_ms' : 123456789
        }
        
        media_result = HF.GetFakeMediaResult( hash )
        
        media_result.GetTimesManager().SetPreviouslyImportedTimestampMS( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, HydrusTime.GetNowMS() )
        
        result_timestamp_data = ClientTime.TimestampData( HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED, location = CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, timestamp_ms = 123456789 )
        
        jobs.append( ( request_args, media_result, HC.CONTENT_UPDATE_SET, result_timestamp_data ) )
        
        #
        
        for ( request_args, media_result, action, result_timestamp_data ) in jobs:
            
            TG.test_controller.SetRead( 'media_results', [ media_result ] )
            
            TG.test_controller.ClearWrites( 'content_updates' )
            
            path = '/edit_times/set_time'
            
            body_dict = { 'hash' : hash_hex }
            body_dict.update( request_args )
            
            body = json.dumps( body_dict )
            
            connection.request( 'POST', path, body = body, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            self.assertEqual( response.status, 200 )
            
            content_update_package = ClientContentUpdates.ContentUpdatePackage()
            
            expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_TIMESTAMP, action, ( [ media_result.GetHash() ], result_timestamp_data ) ) ] )
            
            [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
            
            HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
            
        
        #
        
        problem_jobs = []
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_ARCHIVED
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'timestamp_ms' : 123456789
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_MODIFIED_AGGREGATE,
            'timestamp_ms' : 123456789
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        # wrong service type * 3
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_IMPORTED,
            'timestamp_ms' : 123456789,
            'file_service_key' : CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_DELETED,
            'timestamp_ms' : 123456789,
            'file_service_key' : CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED,
            'timestamp_ms' : 123456789,
            'file_service_key' : CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        # missing service * 3
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_IMPORTED,
            'timestamp_ms' : 123456789,
            'file_service_key' : os.urandom( 32 ).hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_DELETED,
            'timestamp_ms' : 123456789,
            'file_service_key' : os.urandom( 32 ).hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED,
            'timestamp_ms' : 123456789,
            'file_service_key' : os.urandom( 32 ).hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        # trying to delete from file service * 3
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_IMPORTED,
            'timestamp_ms' : None,
            'file_service_key' : CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY.hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_DELETED,
            'timestamp_ms' : None,
            'file_service_key' : CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY.hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        #
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_PREVIOUSLY_IMPORTED,
            'timestamp_ms' : None,
            'file_service_key' : CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY.hex()
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        # no domain
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_MODIFIED_DOMAIN,
            'timestamp_ms' : 123456789
        }
        
        problem_jobs.append( ( request_args, 400 ) )
            
        # wrong canvas type
        
        request_args = {
            'timestamp_type' : HC.TIMESTAMP_TYPE_LAST_VIEWED,
            'canvas_type' : CC.CANVAS_MEDIA_VIEWER_DUPLICATES,
            'timestamp_ms' : 123456789
        }
        
        problem_jobs.append( ( request_args, 400 ) )
        
        for ( request_args, expected_status ) in problem_jobs:
            
            TG.test_controller.ClearWrites( 'content_updates' )
            
            path = '/edit_times/set_time'
            
            body_dict = { 'hash' : hash_hex }
            body_dict.update( request_args )
            
            body = json.dumps( body_dict )
            
            connection.request( 'POST', path, body = body, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            self.assertEqual( response.status, expected_status )
            
        
    
    def _test_add_tags( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        # clean tags
        
        tags = [ " bikini ", "blue    eyes", " character : samus aran ", ":)", "   ", "", "10", "11", "9", "system:wew", "-flower" ]
        
        json_tags = json.dumps( tags )
        
        path = '/add_tags/clean_tags?tags={}'.format( urllib.parse.quote( json_tags, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {}
        
        clean_tags = [ "bikini", "blue eyes", "character:samus aran", "::)", "10", "11", "9", "wew", "flower" ]
        
        clean_tags = HydrusTags.SortNumericTags( clean_tags )
        
        expected_result[ 'tags' ] = clean_tags
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # add tags
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        hash2 = os.urandom( 32 )
        hash2_hex = hash2.hex()
        
        # missing hashes
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 )
        
        # invalid service key
        
        path = '/add_tags/add_tags'
        
        not_existing_service_key_hex = os.urandom( 32 ).hex()
        
        body_dict = { 'hash' : hash_hex, 'service_keys_to_tags' : { not_existing_service_key_hex : [ 'test' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 )
        
        text = str( data, 'utf-8' )
        
        self.assertIn( not_existing_service_key_hex, text ) # test it complains about the key in the error
        
        # add tags to local
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test', { hash } ) ), ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test2', { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # add tags to local complex
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_keys_to_actions_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : { str( HC.CONTENT_UPDATE_ADD ) : [ 'test_add', 'test_add2' ], str( HC.CONTENT_UPDATE_DELETE ) : [ 'test_delete', 'test_delete2' ] } } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, [
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test_add', { hash } ) ),
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test_add2', { hash } ) ),
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test_delete', { hash } ) ),
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test_delete2', { hash } ) )
        ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # pend tags to repo
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_keys_to_tags' : { TG.test_controller.example_tag_repo_service_key.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_tag_repo_service_key, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'test', { hash } ) ), ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'test2', { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # pend tags to repo complex
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_keys_to_actions_to_tags' : { TG.test_controller.example_tag_repo_service_key.hex() : { str( HC.CONTENT_UPDATE_PEND ) : [ 'test_add', 'test_add2' ], str( HC.CONTENT_UPDATE_PETITION ) : [ [ 'test_delete', 'muh reason' ], 'test_delete2' ] } } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( TG.test_controller.example_tag_repo_service_key, [
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'test_add', { hash } ) ),
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'test_add2', { hash } ) ),
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'test_delete', { hash } ), reason = 'muh reason' ),
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'test_delete2', { hash } ), reason = 'Petitioned from API' )
        ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # add to multiple files
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hashes' : [ hash_hex, hash2_hex ], 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test', { hash, hash2 } ) ), ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test2', { hash, hash2 } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # now testing these two new deletion override parameters
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        # two files. hash_hex is ok, hash2_hex will block
        # 1) override_previously_deleted_mappings
        
        body_dict = {
            'hashes' : [ hash_hex, hash2_hex ],
            'service_keys_to_actions_to_tags' : {
                CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : {
                    str( HC.CONTENT_UPDATE_ADD ) : [ 'test_add' ],
                    str( HC.CONTENT_UPDATE_DELETE ) : [ 'test_delete' ]
                }
            },
            'override_previously_deleted_mappings' : False
        }
        
        media_results = [ HF.GetFakeMediaResult( bytes.fromhex( hash_hex ) ) for hash_hex in [ hash_hex, hash2_hex ] ]
        
        # cannot add when there is a deletion record
        media_results[1].GetTagsManager().ProcessContentUpdate( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test_add', { hash2 } ) ) )
        
        TG.test_controller.SetRead( 'media_results', media_results )
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, [
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test_add', { hash } ) ),
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test_delete', { hash, hash2 } ) )
        ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # 2) create_new_deleted_mappings
        
        body_dict = {
            'hashes' : [ hash_hex, hash2_hex ],
            'service_keys_to_actions_to_tags' : {
                CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : {
                    str( HC.CONTENT_UPDATE_ADD ) : [ 'test_add' ],
                    str( HC.CONTENT_UPDATE_DELETE ) : [ 'test_delete' ]
                }
            },
            'create_new_deleted_mappings' : False
        }
        
        media_results = [ HF.GetFakeMediaResult( bytes.fromhex( hash_hex ) ) for hash_hex in [ hash_hex, hash2_hex ] ]
        
        # can only delete when it already exists
        media_results[0].GetTagsManager().ProcessContentUpdate( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test_delete', { hash } ) ) )
        
        TG.test_controller.SetRead( 'media_results', media_results )
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, [
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test_add', { hash, hash2 } ) ),
            ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test_delete', { hash } ) )
        ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
    
    def _test_add_favourite_tags( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        #
        
        def test_favourite_tags( expected_tags ):
            
            path = '/add_tags/get_favourite_tags'
            
            headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            text = str( data, 'utf-8' )
            
            self.assertEqual( response.status, 200 )
            
            d = json.loads( text )
            
            self.assertEqual( expected_tags, d[ 'favourite_tags' ] )
            
        
        test_favourite_tags( [] )
        
        #
        
        path = '/add_tags/set_favourite_tags'
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        request_dict = {
            'set' : [
                "1",
                "11",
                "3",
                "2"
            ]
        }
        
        expected_tags = [ "1", "2", "3", "11" ]
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( expected_tags, d[ 'favourite_tags' ] )
        
        test_favourite_tags( expected_tags )
        
        #
        
        path = '/add_tags/set_favourite_tags'
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        request_dict = {
            'add' : [
                "4"
            ],
            'remove' : [
                "2",
                "3"
            ]
        }
        
        expected_tags = [ "1", "4", "11" ]
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( expected_tags, d[ 'favourite_tags' ] )
        
        test_favourite_tags( expected_tags )
        
    
    def _test_add_tags_get_tag_siblings_and_parents( self, connection, set_up_permissions ):
        
        db_data = {}
        
        db_data[ 'blue eyes' ] = {
            CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : [
                {
                    "blue eyes",
                    "blue_eyes",
                    "blue eye",
                    "blue_eye"
                },
                'blue eyes',
                set(),
                set()
            ],
            TG.test_controller.example_tag_repo_service_key : [
                { 'blue eyes' },
                'blue eyes',
                set(),
                set()
            ]
        }
        
        db_data[ 'samus aran' ] = {
            CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : [
                {
                    "samus aran",
                    "samus_aran",
                    "character:samus aran"
                },
                'character:samus aran',
                {
                    "character:samus aran (zero suit)"
                    "cosplay:samus aran"
                },
                {
                    "series:metroid",
                    "studio:nintendo"
                }
            ],
            TG.test_controller.example_tag_repo_service_key : [
                { 'samus aran' },
                'samus aran',
                {
                    "zero suit samus",
                    "samus_aran_(cosplay)"
                },
                set()
            ]
        }
        
        TG.test_controller.SetRead( 'tag_siblings_and_parents_lookup', db_data )
        
        #
        
        api_permissions = set_up_permissions[ 'add_urls' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/add_tags/get_siblings_and_parents?tags={}'.format( urllib.parse.quote( json.dumps( [ 'blue eyes', 'samus aran' ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 403 )
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/add_tags/get_siblings_and_parents?tags={}'.format( urllib.parse.quote( json.dumps( [ 'blue eyes', 'samus aran' ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'services' : GetExampleServicesDict(),
            'tags' : {}
        }
        
        for ( tag, data ) in db_data.items():
            
            tag_dict = {}
            
            for ( service_key, ( siblings, ideal_tag, descendants, ancestors ) ) in data.items():
                
                tag_dict[ service_key.hex() ] = {
                    'siblings' : list( siblings ),
                    'ideal_tag' : ideal_tag,
                    'descendants' : list( descendants ),
                    'ancestors' : list( ancestors )
                }
                
            
            expected_result[ 'tags' ][ tag ] = tag_dict
            
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
    
    def _test_add_tags_search_tags( self, connection, set_up_permissions ):
        
        predicates = [
            ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'green', count = ClientSearchPredicate.PredicateCount( 2, 0, None, None ) ),
            ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, 'green car', count = ClientSearchPredicate.PredicateCount( 5, 0, None, None ) )
        ]
        
        TG.test_controller.SetRead( 'autocomplete_predicates', predicates )
        
        #
        
        api_permissions = set_up_permissions[ 'search_green_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/add_tags/search_tags?search={}'.format( 'gre' )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'tags' : [
                {
                    'value' : 'green',
                    'count' : 2
                }
            ]
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( expected_result, d )
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/add_tags/search_tags?search={}'.format( '' )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'tags' : []
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( expected_result, d )
        
        ( args, kwargs ) = TG.test_controller.GetRead( 'autocomplete_predicates' )[-1]
        
        self.assertEqual( args[0], ClientTags.TAG_DISPLAY_STORAGE )
        
        #
        
        path = '/add_tags/search_tags?search={}'.format( 'gre' )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        # note this also tests sort
        expected_result = {
            'tags' : [
                {
                    'value' : 'green car',
                    'count' : 5
                },
                {
                    'value' : 'green',
                    'count' : 2
                }
            ]
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( expected_result, d )
        
        ( args, kwargs ) = TG.test_controller.GetRead( 'autocomplete_predicates' )[-1]
        
        self.assertEqual( args[0], ClientTags.TAG_DISPLAY_STORAGE )
        
        #
        
        path = '/add_tags/search_tags?search={}&tag_display_type={}'.format( 'gre', 'display' )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        # note this also tests sort
        expected_result = {
            'tags' : [
                {
                    'value' : 'green car',
                    'count' : 5
                },
                {
                    'value' : 'green',
                    'count' : 2
                }
            ]
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( expected_result, d )
        
        ( args, kwargs ) = TG.test_controller.GetRead( 'autocomplete_predicates' )[-1]
        
        self.assertEqual( args[0], ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
        
        #
        
        # the db won't be asked in this case since default rule for all known tags is not to run this search
        path = '/add_tags/search_tags?search={}'.format( urllib.parse.quote( '*' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        # note this also tests sort
        expected_result = {
            'tags' : []
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( expected_result, d )
        
    
    def _test_add_urls( self, connection, set_up_permissions ):
        
        # get url files
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        # none
        
        url = 'https://muhsite.wew/help_compute'
        
        TG.test_controller.SetRead( 'url_statuses', [] )
        
        path = '/add_urls/get_url_files?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {}
        
        expected_result[ 'normalised_url' ] = url
        expected_result[ 'url_file_statuses' ] = []
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # some
        
        url = 'http://safebooru.org/index.php?s=view&page=post&id=2753608'
        normalised_url = 'https://safebooru.org/index.php?id=2753608&page=post&s=view'
        
        hash = os.urandom( 32 )
        
        url_file_statuses = [ ClientImportFiles.FileImportStatus( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, hash, note = 'muh import phrase' ) ]
        json_url_file_statuses = [ { 'status' : CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, 'hash' : hash.hex(), 'note' : 'muh import phrase' } ]
        
        TG.test_controller.SetRead( 'url_statuses', url_file_statuses )
        
        path = '/add_urls/get_url_files?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {}
        
        expected_result[ 'normalised_url' ] = normalised_url
        expected_result[ 'url_file_statuses' ] = json_url_file_statuses
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # get url info
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        # unknown
        
        url = 'https://muhsite.wew/help_compute'
        
        path = '/add_urls/get_url_info?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {}
        
        expected_result[ 'request_url' ] = url
        expected_result[ 'normalised_url' ] = url
        expected_result[ 'url_type' ] = HC.URL_TYPE_UNKNOWN
        expected_result[ 'url_type_string' ] = 'unknown url'
        expected_result[ 'match_name' ] = 'unknown url'
        expected_result[ 'can_parse' ] = False
        expected_result[ 'cannot_parse_reason' ] = 'unknown url class'
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # known
        
        url = 'http://boards.holotower.org/hlgg/res/123456.html'
        request_url = 'https://boards.holotower.org/hlgg/res/123456.json'
        normalised_url = 'https://boards.holotower.org/hlgg/res/123456.html'
        # http so we can test normalised is https
        
        path = '/add_urls/get_url_info?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {}
        
        expected_result[ 'request_url' ] = request_url
        expected_result[ 'normalised_url' ] = normalised_url
        expected_result[ 'url_type' ] = HC.URL_TYPE_WATCHABLE
        expected_result[ 'url_type_string' ] = 'watchable url'
        expected_result[ 'match_name' ] = 'holotower thread'
        expected_result[ 'can_parse' ] = True
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # known post url
        
        url = 'http://safebooru.org/index.php?page=post&s=view&id=2753608'
        normalised_url = 'https://safebooru.org/index.php?id=2753608&page=post&s=view'
        
        hash = os.urandom( 32 )
        
        path = '/add_urls/get_url_info?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {}
        
        expected_result[ 'request_url' ] = normalised_url
        expected_result[ 'normalised_url' ] = normalised_url
        expected_result[ 'url_type' ] = HC.URL_TYPE_POST
        expected_result[ 'url_type_string' ] = 'post url'
        expected_result[ 'match_name' ] = 'safebooru file page'
        expected_result[ 'can_parse' ] = True
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # add url
        
        TG.test_controller.ClearWrites( 'import_url_test' )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        url = 'http://boards.holotower.org/hlgg/res/123456.html'
        
        request_dict = { 'url' : url }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://boards.holotower.org/hlgg/res/123456.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://boards.holotower.org/hlgg/res/123456.html' )
        
        self.assertEqual( TG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set(), ClientTags.ServiceKeysToTags(), None, None, False, None ), {} ) ] )
        
        # with import destination
        
        TG.test_controller.ClearWrites( 'import_url_test' )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        url = 'http://boards.holotower.org/hlgg/res/123456.html'
        
        request_dict = { 'url' : url, 'file_service_key' : CC.LOCAL_FILE_SERVICE_KEY.hex() }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://boards.holotower.org/hlgg/res/123456.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://boards.holotower.org/hlgg/res/123456.html' )
        
        self.assertEqual( TG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set(), ClientTags.ServiceKeysToTags(), None, None, False, ClientLocation.LocationContext.STATICCreateSimple( CC.LOCAL_FILE_SERVICE_KEY ) ), {} ) ] )
        
        # with name
        
        TG.test_controller.ClearWrites( 'import_url_test' )
        
        request_dict = { 'url' : url, 'destination_page_name' : 'muh /tv/' }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://boards.holotower.org/hlgg/res/123456.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://boards.holotower.org/hlgg/res/123456.html' )
        
        self.assertEqual( TG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set(), ClientTags.ServiceKeysToTags(), 'muh /tv/', None, False, None ), {} ) ] )
        
        # with page_key
        
        TG.test_controller.ClearWrites( 'import_url_test' )
        
        page_key = os.urandom( 32 )
        page_key_hex = page_key.hex()
        
        request_dict = { 'url' : url, 'destination_page_key' : page_key_hex }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://boards.holotower.org/hlgg/res/123456.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://boards.holotower.org/hlgg/res/123456.html' )
        
        self.assertEqual( TG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set(), ClientTags.ServiceKeysToTags(), None, page_key, False, None ), {} ) ] )
        
        # add tags and name, and show destination page
        
        TG.test_controller.ClearWrites( 'import_url_test' )
        
        request_dict = { 'url' : url, 'destination_page_name' : 'muh /tv/', 'show_destination_page' : True, 'filterable_tags' : [ 'filename:yo' ], 'service_keys_to_additional_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ '/tv/ thread' ] } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://boards.holotower.org/hlgg/res/123456.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://boards.holotower.org/hlgg/res/123456.html' )
        
        filterable_tags = [ 'filename:yo' ]
        additional_service_keys_to_tags = ClientTags.ServiceKeysToTags( { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { '/tv/ thread' } } )
        
        self.assertEqual( TG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set( filterable_tags ), additional_service_keys_to_tags, 'muh /tv/', None, True, None ), {} ) ] )
        
        # add tags with service key and name, and show destination page
        
        TG.test_controller.ClearWrites( 'import_url_test' )
        
        request_dict = { 'url' : url, 'destination_page_name' : 'muh /tv/', 'show_destination_page' : True, 'filterable_tags' : [ 'filename:yo' ], 'service_keys_to_additional_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ '/tv/ thread' ] } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://boards.holotower.org/hlgg/res/123456.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://boards.holotower.org/hlgg/res/123456.html' )
        
        filterable_tags = [ 'filename:yo' ]
        additional_service_keys_to_tags = ClientTags.ServiceKeysToTags( { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { '/tv/ thread' } } )
        
        self.assertEqual( TG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set( filterable_tags ), additional_service_keys_to_tags, 'muh /tv/', None, True, None ), {} ) ] )
        
    
    def _test_associate_urls( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        # associate url
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        url = 'https://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'url_to_add' : url, 'hash' : hash.hex() }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( [ url ], { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        url = 'https://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'urls_to_add' : [ url ], 'hashes' : [ hash.hex() ] }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        content_update_package = ClientContentUpdates.ContentUpdatePackage()
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( [ url ], { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        url = 'http://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'url_to_delete' : url, 'hash' : hash.hex() }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( [ url ], { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        #
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        url = 'http://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'urls_to_delete' : [ url ], 'hashes' : [ hash.hex() ] }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( [ url ], { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # normalisation - True
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        unnormalised_url = 'https://rule34.xxx/index.php?page=post&id=2588418&s=view'
        normalised_url = 'https://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'urls_to_add' : [ unnormalised_url ], 'hashes' : [ hash.hex() ] }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( [ normalised_url ], { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # normalisation - False
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        unnormalised_url = 'https://rule34.xxx/index.php?page=post&id=2588418&s=view'
        
        request_dict = { 'urls_to_add' : [ unnormalised_url ], 'hashes' : [ hash.hex() ], 'normalise_urls' : False }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( [ unnormalised_url ], { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # normalisation - crazy url now causes no error
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        crazy_nonsense = 'hello'
        
        request_dict = { 'urls_to_add' : [ crazy_nonsense ], 'hashes' : [ hash.hex() ] }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( [ crazy_nonsense ], { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
        # normalisation - crazy url ok here too
        
        TG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        crazy_nonsense = 'hello'
        
        request_dict = { 'urls_to_add' : [ crazy_nonsense ], 'hashes' : [ hash.hex() ], 'normalise_urls' : False }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdates( CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, [ ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( [ crazy_nonsense ], { hash } ) ) ] )
        
        [ ( ( content_update_package, ), kwargs ) ] = TG.test_controller.GetWrite( 'content_updates' )
        
        HF.compare_content_update_packages( self, content_update_package, expected_content_update_package )
        
    
    def _test_manage_cookies( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'manage_headers' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/manage_cookies/get_cookies?domain=somesite.com'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        cookies = d[ 'cookies' ]
        
        self.assertEqual( cookies, [] )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_cookies/set_cookies'
        
        cookies = []
        
        cookies.append( [ 'one', '1', '.somesite.com', '/', HydrusTime.GetNow() + 86400 ] )
        cookies.append( [ 'two', '2', 'somesite.com', '/', HydrusTime.GetNow() + 86400 ] )
        cookies.append( [ 'three', '3', 'wew.somesite.com', '/', HydrusTime.GetNow() + 86400 ] )
        cookies.append( [ 'four', '4', '.somesite.com', '/', None ] )
        
        request_dict = { 'cookies' : cookies }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        path = '/manage_cookies/get_cookies?domain=somesite.com'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        result_cookies = d[ 'cookies' ]
        
        frozen_result_cookies = { tuple( row ) for row in result_cookies }
        frozen_expected_cookies = { tuple( row ) for row in cookies }
        
        self.assertEqual( frozen_result_cookies, frozen_expected_cookies )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_cookies/set_cookies'
        
        cookies = []
        
        cookies.append( [ 'one', None, '.somesite.com', '/', None ] )
        
        request_dict = { 'cookies' : cookies }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        path = '/manage_cookies/get_cookies?domain=somesite.com'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        result_cookies = d[ 'cookies' ]
        
        expected_cookies = []
        
        expected_cookies.append( [ 'two', '2', 'somesite.com', '/', HydrusTime.GetNow() + 86400 ] )
        expected_cookies.append( [ 'three', '3', 'wew.somesite.com', '/', HydrusTime.GetNow() + 86400 ] )
        expected_cookies.append( [ 'four', '4', '.somesite.com', '/', None ] )
        
        frozen_result_cookies = { tuple( row[:-1] ) for row in result_cookies }
        frozen_expected_cookies = { tuple( row[:-1] ) for row in expected_cookies }
        
        self.assertEqual( frozen_result_cookies, frozen_expected_cookies )
        
        result_times = [ row[-1] for row in sorted( result_cookies ) ]
        expected_times = [ row[-1] for row in sorted( expected_cookies ) ]
        
        for ( a, b ) in zip( result_times, expected_times ):
            
            if a is None:
                
                self.assertIsNone( b )
                
            elif b is None:
                
                self.assertIsNone( a )
                
            else:
                
                self.assertIn( a, ( b - 1, b, b + 1 ) )
                
            
        
        #
        
    
    def _test_manage_headers( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'manage_headers' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_headers/set_user_agent'
        
        new_user_agent = 'muh user agent'
        
        request_dict = { 'user-agent' : new_user_agent }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        current_headers = TG.test_controller.network_engine.domain_manager.GetHeaders( [ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ] )
        
        self.assertEqual( current_headers[ 'User-Agent' ], new_user_agent )
        
        #
        
        request_dict = { 'user-agent' : '' }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        current_headers = TG.test_controller.network_engine.domain_manager.GetHeaders( [ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ] )
        
        from hydrus.client import ClientDefaults
        
        self.assertEqual( current_headers[ 'User-Agent' ], ClientDefaults.DEFAULT_USER_AGENT )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/manage_headers/get_headers'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'network_context' : {
                'type' : 0,
                'data' : None
            },
            'headers' : {
                'User-Agent' : {
                    'approved': 'approved',
                    'reason': 'This is the default User-Agent identifier for the client for all network connections.',
                    'value' : ClientDefaults.DEFAULT_USER_AGENT
                },
                'Cache-Control': {
                    'approved': 'approved',
                    'reason': 'Tells CDNs not to deliver "optimised" versions of files. May not be honoured.',
                    'value': 'no-transform'
                },
                'Accept': {
                    'approved': 'approved',
                    'reason': 'Prefers jpeg/png over webp, but provides graceful fallback.',
                    'value': 'image/jpeg,image/png,image/*;q=0.9,*/*;q=0.8'
                },
            }
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_headers/set_headers'
        
        request_dict = { 'headers' : { 'Test' : { 'value' : 'test_value' } } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/manage_headers/get_headers'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'network_context' : {
                'type' : 0,
                'data' : None
            },
            'headers' : {
                'User-Agent' : {
                    'approved': 'approved',
                    'reason': 'This is the default User-Agent identifier for the client for all network connections.',
                    'value' : ClientDefaults.DEFAULT_USER_AGENT
                },
                'Cache-Control': {
                    'approved': 'approved',
                    'reason': 'Tells CDNs not to deliver "optimised" versions of files. May not be honoured.',
                    'value': 'no-transform'
                },
                'Accept': {
                    'approved': 'approved',
                    'reason': 'Prefers jpeg/png over webp, but provides graceful fallback.',
                    'value': 'image/jpeg,image/png,image/*;q=0.9,*/*;q=0.8'
                },
                'Test' : {
                    'approved': 'approved',
                    'reason': 'Set by Client API',
                    'value' : 'test_value'
                },
            }
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_headers/set_headers'
        
        request_dict = { 'domain' : None, 'headers' : { 'Test' : { 'value' : 'test_value2' } } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/manage_headers/get_headers'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'network_context' : {
                'type' : 0,
                'data' : None
            },
            'headers' : {
                'User-Agent' : {
                    'approved': 'approved',
                    'reason': 'This is the default User-Agent identifier for the client for all network connections.',
                    'value' : ClientDefaults.DEFAULT_USER_AGENT
                },
                'Cache-Control': {
                    'approved': 'approved',
                    'reason': 'Tells CDNs not to deliver "optimised" versions of files. May not be honoured.',
                    'value': 'no-transform'
                },
                'Accept': {
                    'approved': 'approved',
                    'reason': 'Prefers jpeg/png over webp, but provides graceful fallback.',
                    'value': 'image/jpeg,image/png,image/*;q=0.9,*/*;q=0.8'
                },
                'Test' : {
                    'approved': 'approved',
                    'reason': 'Set by Client API',
                    'value' : 'test_value2'
                }
            }
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        #
        
        domain = 'subdomain.example.com'
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = f'/manage_headers/get_headers?domain={domain}'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'network_context' : {
                'type' : 2,
                'data' : 'subdomain.example.com'
            },
            'headers' : {}
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_headers/set_headers'
        
        request_dict = { 'domain' : 'subdomain.example.com', 'headers' : { 'cool_stuff' : { 'value' : 'on', 'approved' : 'pending', 'reason' : 'select yes to turn on cool stuff' } } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/manage_headers/get_headers?domain=subdomain.example.com'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'network_context' : {
                'type' : 2,
                'data' : 'subdomain.example.com'
            },
            'headers' : {
                'cool_stuff' : { 'value' : 'on', 'approved' : 'pending', 'reason' : 'select yes to turn on cool stuff' }
            }
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_headers/set_headers'
        
        request_dict = { 'domain' : 'subdomain.example.com', 'headers' : { 'cool_stuff' : { 'approved' : 'approved' } } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/manage_headers/get_headers?domain=subdomain.example.com'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'network_context' : {
                'type' : 2,
                'data' : 'subdomain.example.com'
            },
            'headers' : {
                'cool_stuff' : { 'value' : 'on', 'approved' : 'approved', 'reason' : 'select yes to turn on cool stuff' }
            }
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_headers/set_headers'
        
        request_dict = { 'domain' : 'subdomain.example.com', 'headers' : { 'cool_stuff' : { 'value' : None } } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/manage_headers/get_headers?domain=subdomain.example.com'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'network_context' : {
                'type' : 2,
                'data' : 'subdomain.example.com'
            },
            'headers' : {}
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
    
    def _test_manage_database( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        self.assertFalse( HG.client_busy.locked() )
        
        path = '/manage_database/lock_on'
        
        connection.request( 'POST', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertTrue( HG.client_busy.locked() )
        
        #
        
        path = '/manage_pages/get_pages'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 503 )
        
        #
        
        path = '/manage_database/lock_off'
        
        connection.request( 'POST', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertFalse( HG.client_busy.locked() )
        
        #
        
        expected_data = { 'hell forever' : 666 }
        
        TG.test_controller.SetRead( 'boned_stats', expected_data )
        
        path = '/manage_database/mr_bones'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        boned_stats = d[ 'boned_stats' ]
        
        self.assertEqual( boned_stats, dict( expected_data ) )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'boned_stats' )
        
        file_search_context = kwargs[ 'file_search_context' ]
        
        self.assertEqual( len( file_search_context.GetPredicates() ), 0 )
        
        #
        
        TG.test_controller.SetRead( 'boned_stats', expected_data )
        
        path = '/manage_database/mr_bones?tags={}'.format( urllib.parse.quote( json.dumps( [ 'skirt', 'blue_eyes' ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        boned_stats = d[ 'boned_stats' ]
        
        self.assertEqual( boned_stats, dict( expected_data ) )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'boned_stats' )
        
        file_search_context = kwargs[ 'file_search_context' ]
        
        self.assertEqual( len( file_search_context.GetPredicates() ), 2 )
        
    
    def _test_manage_duplicates( self, connection, set_up_permissions ):
        
        # this stuff is super dependent on the db requests, which aren't tested in this class, but we can do the arg parsing and wrapper
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        default_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        # file relationships
        
        file_relationships_hash = bytes.fromhex( 'ac940bb9026c430ea9530b4f4f6980a12d9432c2af8d9d39dfc67b05d91df11d' )
        
        # yes the database returns hex hashes in this case
        example_response = {
            "file_relationships" : {
                "ac940bb9026c430ea9530b4f4f6980a12d9432c2af8d9d39dfc67b05d91df11d" : {
                    "is_king" : False,
                    "king" : "8784afbfd8b59de3dcf2c13dc1be9d7cb0b3d376803c8a7a8b710c7c191bb657",
                    "king_is_on_file_domain" : True,
                    "king_is_local" : True,
                    "0" : [
                    ],
                    "1" : [],
                    "3" : [
                        "8bf267c4c021ae4fd7c4b90b0a381044539519f80d148359b0ce61ce1684fefe"
                    ],
                    "8" : [
                        "8784afbfd8b59de3dcf2c13dc1be9d7cb0b3d376803c8a7a8b710c7c191bb657",
                        "3fa8ef54811ec8c2d1892f4f08da01e7fc17eed863acae897eb30461b051d5c3"
                    ]
                }
            }
        }
        
        TG.test_controller.SetRead( 'file_relationships_for_api', example_response )
        
        path = '/manage_file_relationships/get_file_relationships?hash={}'.format( file_relationships_hash.hex() )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'file_relationships' ], example_response )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_relationships_for_api' )

        ( location_context, hashes ) = args
        
        self.assertEqual( location_context, default_location_context )
        self.assertEqual( set( hashes ), { file_relationships_hash } )
        
        # search files failed tag permission
        
        tag_context = ClientSearchTagContext.TagContext( CC.COMBINED_TAG_SERVICE_KEY )
        predicates = { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING ) }
        
        default_file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context, tag_context = tag_context, predicates = predicates )
        
        default_potentials_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
        default_pixel_duplicates = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        default_max_hamming_distance = 4
        
        test_tag_service_key_1 = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
        test_tags_1 = [ 'skirt', 'system:width<400' ]
        
        test_tag_context_1 = ClientSearchTagContext.TagContext( test_tag_service_key_1 )
        test_predicates_1 = ClientLocalServerCore.ConvertTagListToPredicates( None, test_tags_1, do_permission_check = False )
        
        test_file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context, tag_context = test_tag_context_1, predicates = test_predicates_1 )
        
        test_tag_service_key_2 = TG.test_controller.example_tag_repo_service_key
        test_tags_2 = [ 'system:untagged' ]
        
        test_tag_context_2 = ClientSearchTagContext.TagContext( test_tag_service_key_2 )
        test_predicates_2 = ClientLocalServerCore.ConvertTagListToPredicates( None, test_tags_2, do_permission_check = False )
        
        test_file_search_context_2 = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context, tag_context = test_tag_context_2, predicates = test_predicates_2 )
        
        test_potentials_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES
        test_pixel_duplicates = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED
        test_max_hamming_distance = 8
        
        # get count
        
        TG.test_controller.SetRead( 'potential_duplicates_count', 5 )
        
        path = '/manage_file_relationships/get_potentials_count'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'potential_duplicates_count' ], 5 )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'potential_duplicates_count' )

        ( potential_duplicates_search_context, ) = args
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        potentials_search_type = potential_duplicates_search_context.GetDupeSearchType()
        pixel_duplicates = potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = potential_duplicates_search_context.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), default_file_search_context.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), default_file_search_context.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, default_potentials_search_type )
        self.assertEqual( pixel_duplicates, default_pixel_duplicates )
        self.assertEqual( max_hamming_distance, default_max_hamming_distance )
        
        # get count with params
        
        TG.test_controller.SetRead( 'potential_duplicates_count', 5 )
        
        path = '/manage_file_relationships/get_potentials_count?tag_service_key_1={}&tags_1={}&tag_service_key_2={}&tags_2={}&potentials_search_type={}&pixel_duplicates={}&max_hamming_distance={}'.format(
            test_tag_service_key_1.hex(),
            urllib.parse.quote( json.dumps( test_tags_1 ) ),
            test_tag_service_key_2.hex(),
            urllib.parse.quote( json.dumps( test_tags_2 ) ),
            test_potentials_search_type,
            test_pixel_duplicates,
            test_max_hamming_distance
        )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'potential_duplicates_count' ], 5 )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'potential_duplicates_count' )

        ( potential_duplicates_search_context, ) = args
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        potentials_search_type = potential_duplicates_search_context.GetDupeSearchType()
        pixel_duplicates = potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = potential_duplicates_search_context.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), test_file_search_context_1.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), test_file_search_context_2.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, test_potentials_search_type )
        self.assertEqual( pixel_duplicates, test_pixel_duplicates )
        self.assertEqual( max_hamming_distance, test_max_hamming_distance )
        
        #
        
        # set relationship
        
        # this is tricky to test fully
        
        TG.test_controller.ClearWrites( 'duplicate_pair_status' )
        
        TG.test_controller.ClearReads( 'media_result' )
        
        hashes = {
            'b54d09218e0d6efc964b78b070620a1fa19c7e069672b4c6313cee2c9b0623f2',
            'bbaa9876dab238dcf5799bfd8319ed0bab805e844f45cf0de33f40697b11a845',
            '22667427eaa221e2bd7ef405e1d2983846c863d40b2999ce8d1bf5f0c18f5fb2',
            '65d228adfa722f3cd0363853a191898abe8bf92d9a514c6c7f3c89cfed0bf423',
            '0480513ffec391b77ad8c4e57fe80e5b710adfa3cb6af19b02a0bd7920f2d3ec',
            '5fab162576617b5c3fc8caabea53ce3ab1a3c8e0a16c16ae7b4e4a21eab168a7'
        }
        
        # TODO: populate the fakes here with real tags and test actual content merge
        # to test the content merge, we'd want to set some content merge options and populate these fakes with real tags
        # don't need to be too clever, just test one thing and we know it'll all be hooked up right
        TG.test_controller.SetRead( 'media_results', [ HF.GetFakeMediaResult( bytes.fromhex( hash_hex ) ) for hash_hex in hashes ] )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_file_relationships/set_file_relationships'
        
        request_dict = {
            "relationships" : [
                {
                    "hash_a" : "b54d09218e0d6efc964b78b070620a1fa19c7e069672b4c6313cee2c9b0623f2",
                    "hash_b" : "bbaa9876dab238dcf5799bfd8319ed0bab805e844f45cf0de33f40697b11a845",
                    "relationship" : 4,
                    "do_default_content_merge" : False,
                    "delete_b" : True
                },
                {
                    "hash_a" : "22667427eaa221e2bd7ef405e1d2983846c863d40b2999ce8d1bf5f0c18f5fb2",
                    "hash_b" : "65d228adfa722f3cd0363853a191898abe8bf92d9a514c6c7f3c89cfed0bf423",
                    "relationship" : 4,
                    "do_default_content_merge" : False,
                    "delete_b" : True
                },
                {
                    "hash_a" : "0480513ffec391b77ad8c4e57fe80e5b710adfa3cb6af19b02a0bd7920f2d3ec",
                    "hash_b" : "5fab162576617b5c3fc8caabea53ce3ab1a3c8e0a16c16ae7b4e4a21eab168a7",
                    "relationship" : 2,
                    "do_default_content_merge" : False
                }
            ]
        }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetWrite( 'duplicate_pair_status' )

        ( written_rows, ) = args
        
        self.assertTrue( len( written_rows ) == 3 )
        
        for ( i, row ) in enumerate( written_rows ):
            
            r_dict = request_dict[ 'relationships' ][i]
            
            self.assertEqual( row[0], r_dict[ 'relationship' ] )
            self.assertEqual( row[1], bytes.fromhex( r_dict[ 'hash_a' ] ) )
            self.assertEqual( row[2], bytes.fromhex( r_dict[ 'hash_b' ] ) )
            
            do_delete = 'delete_b' in r_dict and r_dict[ 'delete_b' ]
            
            content_update_packages = row[3]
            
            if do_delete:
                
                self.assertTrue( len( content_update_packages ) == 1 )
                
                expected_content_update_package = ClientContentUpdates.ContentUpdatePackage.STATICCreateFromContentUpdate( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, ClientContentUpdates.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { bytes.fromhex( r_dict[ 'hash_b' ] ) }, reason = 'From Client API (duplicates processing).' ) )
                
                HF.compare_content_update_packages( self, content_update_packages[0], expected_content_update_package )
                
            else:
                
                self.assertTrue( len( content_update_packages ) == 0 )
                
            
        
        # remove potentials
        
        TG.test_controller.ClearWrites( 'remove_potential_pairs' )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_file_relationships/remove_potentials'
        
        test_hashes = [
            "b54d09218e0d6efc964b78b070620a1fa19c7e069672b4c6313cee2c9b0623f2",
            "bbaa9876dab238dcf5799bfd8319ed0bab805e844f45cf0de33f40697b11a845"
        ]
        
        request_dict = { 'hashes' : test_hashes }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetWrite( 'remove_potential_pairs' )
        
        self.assertEqual( set( args[0] ), { bytes.fromhex( h ) for h in test_hashes } )
        
        # set kings
        
        TG.test_controller.ClearWrites( 'duplicate_set_king' )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_file_relationships/set_kings'
        
        test_hashes = [
            "b54d09218e0d6efc964b78b070620a1fa19c7e069672b4c6313cee2c9b0623f2",
            "bbaa9876dab238dcf5799bfd8319ed0bab805e844f45cf0de33f40697b11a845"
        ]
        
        request_dict = { 'hashes' : test_hashes }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( args1, kwargs1 ), ( args2, kwargs2 ) ] = TG.test_controller.GetWrite( 'duplicate_set_king' )
        
        self.assertEqual( { args1[0], args2[0] }, { bytes.fromhex( h ) for h in test_hashes } )
        
    
    def _test_manage_duplicate_potential_pairs( self, connection, set_up_permissions ):
        
        def fragmentary_fetch_factory( result ):
            
            def the_callable( fragmentary_search, *args, **kwargs ):
                
                while not fragmentary_search.SearchDone():
                    
                    fragmentary_search.PopBlock()
                    
                
                return result
                
            
            return the_callable
            
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        default_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        #
        
        tag_context = ClientSearchTagContext.TagContext( CC.COMBINED_TAG_SERVICE_KEY )
        predicates = [ ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_EVERYTHING ) ]
        
        default_file_search_context = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context, tag_context = tag_context, predicates = predicates )
        
        default_potentials_search_type = ClientDuplicates.DUPE_SEARCH_ONE_FILE_MATCHES_ONE_SEARCH
        default_pixel_duplicates = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_ALLOWED
        default_max_hamming_distance = 4
        
        test_tag_service_key_1 = CC.DEFAULT_LOCAL_TAG_SERVICE_KEY
        test_tags_1 = [ 'skirt', 'system:width<400' ]
        
        test_tag_context_1 = ClientSearchTagContext.TagContext( test_tag_service_key_1 )
        test_predicates_1 = ClientLocalServerCore.ConvertTagListToPredicates( None, test_tags_1, do_permission_check = False )
        
        test_file_search_context_1 = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context, tag_context = test_tag_context_1, predicates = test_predicates_1 )
        
        test_tag_service_key_2 = TG.test_controller.example_tag_repo_service_key
        test_tags_2 = [ 'system:untagged' ]
        
        test_tag_context_2 = ClientSearchTagContext.TagContext( test_tag_service_key_2 )
        test_predicates_2 = ClientLocalServerCore.ConvertTagListToPredicates( None, test_tags_2, do_permission_check = False )
        
        test_file_search_context_2 = ClientSearchFileSearchContext.FileSearchContext( location_context = default_location_context, tag_context = test_tag_context_2, predicates = test_predicates_2 )
        
        test_potentials_search_type = ClientDuplicates.DUPE_SEARCH_BOTH_FILES_MATCH_DIFFERENT_SEARCHES
        test_pixel_duplicates = ClientDuplicates.SIMILAR_FILES_PIXEL_DUPES_EXCLUDED
        test_max_hamming_distance = 8
        
        #
        
        test_mr_pairs_and_distances = []
        
        hash_id = 0
        
        for i in range( 20 ):
            
            mr_1 = HF.GetFakeMediaResult( os.urandom( 32 ) )
            mr_2 = HF.GetFakeMediaResult( os.urandom( 32 ) )
            
            mr_1.GetFileInfoManager().size = random.randint( 500, 50000 )
            mr_2.GetFileInfoManager().size = random.randint( 500, 50000 )
            
            if mr_1.GetFileInfoManager().size == mr_2.GetFileInfoManager().size:
                mr_2.GetFileInfoManager().size = mr_1.GetFileInfoManager().size + 1
            
            mr_1.GetFileInfoManager().hash_id = hash_id
            hash_id += 1
            
            mr_2.GetFileInfoManager().hash_id = hash_id
            hash_id += 1
            
            test_mr_pairs_and_distances.append( ( mr_1, mr_2, 0 ) )
            
        
        test_potential_duplicate_id_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances(
            [ ( mr_1.GetFileInfoManager().hash_id, mr_2.GetFileInfoManager().hash_id, distance ) for ( mr_1, mr_2, distance ) in test_mr_pairs_and_distances ]
        )
        
        test_potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( test_mr_pairs_and_distances )
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate = test_potential_duplicate_media_result_pairs_and_distances.Duplicate()
        
        path = '/manage_file_relationships/get_potential_pairs'
        
        read_db_side_effect = HF.DBSideEffect()
        read_db_side_effect.AddResult( 'potential_duplicate_id_pairs_and_distances', test_potential_duplicate_id_pairs_and_distances )
        read_db_side_effect.AddCallable( 'potential_duplicate_media_result_pairs_and_distances_fragmentary', fragmentary_fetch_factory( test_potential_duplicate_media_result_pairs_and_distances ) )
        
        with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ) as read_mock_object:
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            all_read_calls = read_mock_object.call_args_list
            
            self.assertEqual( len( all_read_calls ), 2 )
            
            self.assertEqual( all_read_calls[0].args[0], 'potential_duplicate_id_pairs_and_distances' )
            self.assertEqual( all_read_calls[0].args[1], default_location_context )
            
            self.assertEqual( all_read_calls[1].args[0], 'potential_duplicate_media_result_pairs_and_distances_fragmentary' )
            self.assertTrue( isinstance( all_read_calls[1].args[1], ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) )
            
            read_potential_duplicates_search_context = all_read_calls[1].args[1].GetPotentialDuplicatesSearchContext()
            
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        hashes_we_got_back_hex = d[ 'potential_duplicate_pairs' ]
        hashes_we_got_back = [ ( bytes.fromhex( hash_hex_1 ), bytes.fromhex( hash_hex_2 ) ) for ( hash_hex_1, hash_hex_2 ) in hashes_we_got_back_hex ]
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.Sort( ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE, False )
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.ABPairsUsingFastComparisonScore()
        
        hashes_we_expect = [ ( mr_1.GetHash(), mr_2.GetHash() ) for ( mr_1, mr_2 ) in test_potential_duplicate_media_result_pairs_and_distances_duplicate.GetPairs() ]
        
        self.assertEqual( hashes_we_got_back, hashes_we_expect )
        
        file_search_context_1 = read_potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = read_potential_duplicates_search_context.GetFileSearchContext2()
        potentials_search_type = read_potential_duplicates_search_context.GetDupeSearchType()
        pixel_duplicates = read_potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = read_potential_duplicates_search_context.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), default_file_search_context.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), default_file_search_context.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, default_potentials_search_type )
        self.assertEqual( pixel_duplicates, default_pixel_duplicates )
        self.assertEqual( max_hamming_distance, default_max_hamming_distance )
        
        # get pairs with params
        
        test_potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( test_mr_pairs_and_distances )
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate = test_potential_duplicate_media_result_pairs_and_distances.Duplicate()
        
        path = '/manage_file_relationships/get_potential_pairs?tag_service_key_1={}&tags_1={}&tag_service_key_2={}&tags_2={}&potentials_search_type={}&pixel_duplicates={}&max_hamming_distance={}'.format(
            test_tag_service_key_1.hex(),
            urllib.parse.quote( json.dumps( test_tags_1 ) ),
            test_tag_service_key_2.hex(),
            urllib.parse.quote( json.dumps( test_tags_2 ) ),
            test_potentials_search_type,
            test_pixel_duplicates,
            test_max_hamming_distance
        )
        
        read_db_side_effect = HF.DBSideEffect()
        read_db_side_effect.AddResult( 'potential_duplicate_id_pairs_and_distances', test_potential_duplicate_id_pairs_and_distances )
        read_db_side_effect.AddCallable( 'potential_duplicate_media_result_pairs_and_distances_fragmentary', fragmentary_fetch_factory( test_potential_duplicate_media_result_pairs_and_distances ) )
        
        with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ) as read_mock_object:
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            all_read_calls = read_mock_object.call_args_list
            
            self.assertEqual( len( all_read_calls ), 2 )
            
            self.assertEqual( all_read_calls[0].args[0], 'potential_duplicate_id_pairs_and_distances' )
            self.assertEqual( all_read_calls[0].args[1], default_location_context )
            
            self.assertEqual( all_read_calls[1].args[0], 'potential_duplicate_media_result_pairs_and_distances_fragmentary' )
            self.assertTrue( isinstance( all_read_calls[1].args[1], ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) )
            
            read_potential_duplicates_search_context = all_read_calls[1].args[1].GetPotentialDuplicatesSearchContext()
            
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        hashes_we_got_back_hex = d[ 'potential_duplicate_pairs' ]
        hashes_we_got_back = [ ( bytes.fromhex( hash_hex_1 ), bytes.fromhex( hash_hex_2 ) ) for ( hash_hex_1, hash_hex_2 ) in hashes_we_got_back_hex ]
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.Sort( ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE, False )
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.ABPairsUsingFastComparisonScore()
        
        hashes_we_expect = [ ( mr_1.GetHash(), mr_2.GetHash() ) for ( mr_1, mr_2 ) in test_potential_duplicate_media_result_pairs_and_distances_duplicate.GetPairs() ]
        
        self.assertEqual( hashes_we_got_back, hashes_we_expect )
        
        file_search_context_1 = read_potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = read_potential_duplicates_search_context.GetFileSearchContext2()
        potentials_search_type = read_potential_duplicates_search_context.GetDupeSearchType()
        pixel_duplicates = read_potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = read_potential_duplicates_search_context.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), test_file_search_context_1.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), test_file_search_context_2.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, test_potentials_search_type )
        self.assertEqual( pixel_duplicates, test_pixel_duplicates )
        self.assertEqual( max_hamming_distance, test_max_hamming_distance )
        
        # get pairs with max num
        
        test_potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( test_mr_pairs_and_distances )
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate = test_potential_duplicate_media_result_pairs_and_distances.Duplicate()
        
        test_max_num_pairs = 10
        
        path = '/manage_file_relationships/get_potential_pairs?tag_service_key_1={}&tags_1={}&tag_service_key_2={}&tags_2={}&potentials_search_type={}&pixel_duplicates={}&max_hamming_distance={}&max_num_pairs={}'.format(
            test_tag_service_key_1.hex(),
            urllib.parse.quote( json.dumps( test_tags_1 ) ),
            test_tag_service_key_2.hex(),
            urllib.parse.quote( json.dumps( test_tags_2 ) ),
            test_potentials_search_type,
            test_pixel_duplicates,
            test_max_hamming_distance,
            test_max_num_pairs
        )
        
        read_db_side_effect = HF.DBSideEffect()
        read_db_side_effect.AddResult( 'potential_duplicate_id_pairs_and_distances', test_potential_duplicate_id_pairs_and_distances )
        read_db_side_effect.AddCallable( 'potential_duplicate_media_result_pairs_and_distances_fragmentary', fragmentary_fetch_factory( test_potential_duplicate_media_result_pairs_and_distances ) )
        
        with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ) as read_mock_object:
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            all_read_calls = read_mock_object.call_args_list
            
            self.assertEqual( len( all_read_calls ), 2 )
            
            self.assertEqual( all_read_calls[0].args[0], 'potential_duplicate_id_pairs_and_distances' )
            self.assertEqual( all_read_calls[0].args[1], default_location_context )
            
            self.assertEqual( all_read_calls[1].args[0], 'potential_duplicate_media_result_pairs_and_distances_fragmentary' )
            self.assertTrue( isinstance( all_read_calls[1].args[1], ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) )
            
            read_potential_duplicates_search_context = all_read_calls[1].args[1].GetPotentialDuplicatesSearchContext()
            
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        hashes_we_got_back_hex = d[ 'potential_duplicate_pairs' ]
        hashes_we_got_back = [ ( bytes.fromhex( hash_hex_1 ), bytes.fromhex( hash_hex_2 ) ) for ( hash_hex_1, hash_hex_2 ) in hashes_we_got_back_hex ]
        
        self.assertEqual( len( hashes_we_got_back ), test_max_num_pairs )
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.Sort( ClientDuplicates.DUPE_PAIR_SORT_MAX_FILESIZE, False )
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.ABPairsUsingFastComparisonScore()
        
        hashes_we_expect = [ ( mr_1.GetHash(), mr_2.GetHash() ) for ( mr_1, mr_2 ) in test_potential_duplicate_media_result_pairs_and_distances_duplicate.GetPairs() ]
        
        self.assertTrue( set( hashes_we_expect ).issuperset( set( hashes_we_got_back ) ) )
        
        hashes_we_got_back_fast = set( hashes_we_got_back )
        
        hashes_we_expect_cut_down_and_in_order = [ pair for pair in hashes_we_expect if pair in hashes_we_got_back_fast ]
        
        self.assertEqual( hashes_we_got_back, hashes_we_expect_cut_down_and_in_order )
        
        file_search_context_1 = read_potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = read_potential_duplicates_search_context.GetFileSearchContext2()
        potentials_search_type = read_potential_duplicates_search_context.GetDupeSearchType()
        pixel_duplicates = read_potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = read_potential_duplicates_search_context.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), test_file_search_context_1.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), test_file_search_context_2.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, test_potentials_search_type )
        self.assertEqual( pixel_duplicates, test_pixel_duplicates )
        self.assertEqual( max_hamming_distance, test_max_hamming_distance )
        
        # now sort them
        
        test_potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( test_mr_pairs_and_distances )
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate = test_potential_duplicate_media_result_pairs_and_distances.Duplicate()
        
        test_max_num_pairs = 10
        
        path = '/manage_file_relationships/get_potential_pairs?tag_service_key_1={}&tags_1={}&tag_service_key_2={}&tags_2={}&potentials_search_type={}&pixel_duplicates={}&max_hamming_distance={}&max_num_pairs={}&duplicate_pair_sort_type={}&duplicate_pair_sort_asc={}'.format(
            test_tag_service_key_1.hex(),
            urllib.parse.quote( json.dumps( test_tags_1 ) ),
            test_tag_service_key_2.hex(),
            urllib.parse.quote( json.dumps( test_tags_2 ) ),
            test_potentials_search_type,
            test_pixel_duplicates,
            test_max_hamming_distance,
            test_max_num_pairs,
            ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE,
            'true'
        )
        
        read_db_side_effect = HF.DBSideEffect()
        read_db_side_effect.AddResult( 'potential_duplicate_id_pairs_and_distances', test_potential_duplicate_id_pairs_and_distances )
        read_db_side_effect.AddCallable( 'potential_duplicate_media_result_pairs_and_distances_fragmentary', fragmentary_fetch_factory( test_potential_duplicate_media_result_pairs_and_distances ) )
        
        with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ) as read_mock_object:
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            all_read_calls = read_mock_object.call_args_list
            
            self.assertEqual( len( all_read_calls ), 2 )
            
            self.assertEqual( all_read_calls[0].args[0], 'potential_duplicate_id_pairs_and_distances' )
            self.assertEqual( all_read_calls[0].args[1], default_location_context )
            
            self.assertEqual( all_read_calls[1].args[0], 'potential_duplicate_media_result_pairs_and_distances_fragmentary' )
            self.assertTrue( isinstance( all_read_calls[1].args[1], ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) )
            
            read_potential_duplicates_search_context = all_read_calls[1].args[1].GetPotentialDuplicatesSearchContext()
            
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        hashes_we_got_back_hex = d[ 'potential_duplicate_pairs' ]
        hashes_we_got_back = [ ( bytes.fromhex( hash_hex_1 ), bytes.fromhex( hash_hex_2 ) ) for ( hash_hex_1, hash_hex_2 ) in hashes_we_got_back_hex ]
        
        self.assertEqual( len( hashes_we_got_back ), test_max_num_pairs )
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.Sort( ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE, True )
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.ABPairsUsingFastComparisonScore()
        
        hashes_we_expect = [ ( mr_1.GetHash(), mr_2.GetHash() ) for ( mr_1, mr_2 ) in test_potential_duplicate_media_result_pairs_and_distances_duplicate.GetPairs() ]
        
        self.assertTrue( set( hashes_we_expect ).issuperset( set( hashes_we_got_back ) ) )
        
        hashes_we_got_back_fast = set( hashes_we_got_back )
        
        hashes_we_expect_cut_down_and_in_order = [ pair for pair in hashes_we_expect if pair in hashes_we_got_back_fast ]
        
        self.assertEqual( hashes_we_got_back, hashes_we_expect_cut_down_and_in_order )
        
        file_search_context_1 = read_potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = read_potential_duplicates_search_context.GetFileSearchContext2()
        potentials_search_type = read_potential_duplicates_search_context.GetDupeSearchType()
        pixel_duplicates = read_potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = read_potential_duplicates_search_context.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), test_file_search_context_1.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), test_file_search_context_2.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, test_potentials_search_type )
        self.assertEqual( pixel_duplicates, test_pixel_duplicates )
        self.assertEqual( max_hamming_distance, test_max_hamming_distance )
        
        # now group mode
        
        group_test_mr_pairs_and_distances = []
        test_mr_pairs_and_distances = []
        
        hash_id = 0
        
        mr_1 = HF.GetFakeMediaResult( os.urandom( 32 ) )
        mr_1.GetFileInfoManager().size = random.randint( 500, 50000 )
        
        mr_1.GetFileInfoManager().hash_id = hash_id
        hash_id += 1
        
        for i in range( 5 ):
            
            mr_2 = HF.GetFakeMediaResult( os.urandom( 32 ) )
            
            mr_2.GetFileInfoManager().size = random.randint( 500, 50000 )
            
            mr_2.GetFileInfoManager().hash_id = hash_id
            hash_id += 1
            
            group_test_mr_pairs_and_distances.append( ( mr_1, mr_2, 0 ) )
            test_mr_pairs_and_distances.append( ( mr_1, mr_2, 0 ) )
            
        
        for i in range( 20 ):
            
            mr_1 = HF.GetFakeMediaResult( os.urandom( 32 ) )
            mr_2 = HF.GetFakeMediaResult( os.urandom( 32 ) )
            
            mr_1.GetFileInfoManager().size = random.randint( 500, 50000 )
            mr_2.GetFileInfoManager().size = random.randint( 500, 50000 )
            
            mr_1.GetFileInfoManager().hash_id = hash_id
            hash_id += 1
            
            mr_2.GetFileInfoManager().hash_id = hash_id
            hash_id += 1
            
            test_mr_pairs_and_distances.append( ( mr_1, mr_2, 0 ) )
            
        
        test_potential_duplicate_id_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances(
            [ ( mr_1.GetFileInfoManager().hash_id, mr_2.GetFileInfoManager().hash_id, distance ) for ( mr_1, mr_2, distance ) in test_mr_pairs_and_distances ]
        )
        
        group_test_potential_duplicate_id_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateIdPairsAndDistances(
            [ ( mr_1.GetFileInfoManager().hash_id, mr_2.GetFileInfoManager().hash_id, distance ) for ( mr_1, mr_2, distance ) in group_test_mr_pairs_and_distances ]
        )
        
        test_potential_duplicate_media_result_pairs_and_distances = ClientPotentialDuplicatesSearchContext.PotentialDuplicateMediaResultPairsAndDistances( group_test_mr_pairs_and_distances )
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate = test_potential_duplicate_media_result_pairs_and_distances.Duplicate()
        
        path = '/manage_file_relationships/get_potential_pairs?tag_service_key_1={}&tags_1={}&tag_service_key_2={}&tags_2={}&potentials_search_type={}&pixel_duplicates={}&max_hamming_distance={}&duplicate_pair_sort_type={}&duplicate_pair_sort_asc={}&group_mode={}'.format(
            test_tag_service_key_1.hex(),
            urllib.parse.quote( json.dumps( test_tags_1 ) ),
            test_tag_service_key_2.hex(),
            urllib.parse.quote( json.dumps( test_tags_2 ) ),
            test_potentials_search_type,
            test_pixel_duplicates,
            test_max_hamming_distance,
            ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE,
            'true',
            'true'
        )
        
        read_db_side_effect = HF.DBSideEffect()
        read_db_side_effect.AddResult( 'potential_duplicate_id_pairs_and_distances', test_potential_duplicate_id_pairs_and_distances )
        read_db_side_effect.AddResult( 'potential_duplicate_id_pairs_and_distances_fragmentary', group_test_potential_duplicate_id_pairs_and_distances )
        read_db_side_effect.AddResult( 'potential_duplicate_media_result_pairs_and_distances', test_potential_duplicate_media_result_pairs_and_distances )
        
        with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ) as read_mock_object:
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            all_read_calls = read_mock_object.call_args_list
            
            self.assertEqual( len( all_read_calls ), 3 )
            
            self.assertEqual( all_read_calls[0].args[0], 'potential_duplicate_id_pairs_and_distances' )
            self.assertEqual( all_read_calls[0].args[1], default_location_context )
            
            self.assertEqual( all_read_calls[1].args[0], 'potential_duplicate_id_pairs_and_distances_fragmentary' )
            self.assertTrue( isinstance( all_read_calls[1].args[1], ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) )
            
            read_potential_duplicates_search_context_for_ids = all_read_calls[1].args[1].GetPotentialDuplicatesSearchContext()
            read_potential_duplicate_id_pairs_and_distances_for_ids = all_read_calls[1].args[1]._potential_duplicate_id_pairs_and_distances_search_space
            
            self.assertEqual( all_read_calls[2].args[0], 'potential_duplicate_media_result_pairs_and_distances' )
            self.assertTrue( isinstance( all_read_calls[2].args[1], ClientPotentialDuplicatesSearchContext.PotentialDuplicatePairsFragmentarySearch ) )
            
            read_potential_duplicates_search_context_for_media_results = all_read_calls[2].args[1].GetPotentialDuplicatesSearchContext()
            read_potential_duplicate_id_pairs_and_distances_for_media_results = all_read_calls[2].args[1]._potential_duplicate_id_pairs_and_distances_search_space
            
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        hashes_we_got_back_hex = d[ 'potential_duplicate_pairs' ]
        hashes_we_got_back = [ ( bytes.fromhex( hash_hex_1 ), bytes.fromhex( hash_hex_2 ) ) for ( hash_hex_1, hash_hex_2 ) in hashes_we_got_back_hex ]
        
        self.assertEqual( len( hashes_we_got_back ), 5 )
        
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.Sort( ClientDuplicates.DUPE_PAIR_SORT_MIN_FILESIZE, True )
        test_potential_duplicate_media_result_pairs_and_distances_duplicate.ABPairsUsingFastComparisonScore()
        
        hashes_we_expect = [ ( mr_1.GetHash(), mr_2.GetHash() ) for ( mr_1, mr_2 ) in test_potential_duplicate_media_result_pairs_and_distances_duplicate.GetPairs() ]
        
        self.assertTrue( set( hashes_we_expect ).issuperset( set( hashes_we_got_back ) ) )
        
        hashes_we_got_back_fast = set( hashes_we_got_back )
        
        hashes_we_expect_cut_down_and_in_order = [ pair for pair in hashes_we_expect if pair in hashes_we_got_back_fast ]
        
        self.assertEqual( hashes_we_got_back, hashes_we_expect_cut_down_and_in_order )
        
        file_search_context_1 = read_potential_duplicates_search_context_for_ids.GetFileSearchContext1()
        file_search_context_2 = read_potential_duplicates_search_context_for_ids.GetFileSearchContext2()
        potentials_search_type = read_potential_duplicates_search_context_for_ids.GetDupeSearchType()
        pixel_duplicates = read_potential_duplicates_search_context_for_ids.GetPixelDupesPreference()
        max_hamming_distance = read_potential_duplicates_search_context_for_ids.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), test_file_search_context_1.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), test_file_search_context_2.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, test_potentials_search_type )
        self.assertEqual( pixel_duplicates, test_pixel_duplicates )
        self.assertEqual( max_hamming_distance, test_max_hamming_distance )
        
        self.assertEqual( read_potential_duplicate_id_pairs_and_distances_for_ids.GetPairs(), test_potential_duplicate_id_pairs_and_distances.GetPairs() )
        
        self.assertEqual( set( read_potential_duplicate_id_pairs_and_distances_for_media_results.GetPairs() ), set( group_test_potential_duplicate_id_pairs_and_distances.GetPairs() ) ) # jumbled by this point
        
        file_search_context_1 = read_potential_duplicates_search_context_for_media_results.GetFileSearchContext1()
        file_search_context_2 = read_potential_duplicates_search_context_for_media_results.GetFileSearchContext2()
        potentials_search_type = read_potential_duplicates_search_context_for_media_results.GetDupeSearchType()
        pixel_duplicates = read_potential_duplicates_search_context_for_media_results.GetPixelDupesPreference()
        max_hamming_distance = read_potential_duplicates_search_context_for_media_results.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), test_file_search_context_1.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), test_file_search_context_2.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, test_potentials_search_type )
        self.assertEqual( pixel_duplicates, test_pixel_duplicates )
        self.assertEqual( max_hamming_distance, test_max_hamming_distance )
        
        # get random
        
        test_hashes = [ os.urandom( 32 ) for i in range( 6 ) ]
        test_hash_pairs_hex = [ h.hex() for h in test_hashes ]
        
        path = '/manage_file_relationships/get_random_potentials'
        
        read_db_side_effect = HF.DBSideEffect()
        read_db_side_effect.AddResult( 'random_potential_duplicate_hashes', test_hashes )
        
        with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ) as read_mock_object:
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            all_read_calls = read_mock_object.call_args_list
            
            self.assertEqual( len( all_read_calls ), 1 )
            
            self.assertEqual( all_read_calls[0].args[0], 'random_potential_duplicate_hashes' )
            
            potential_duplicates_search_context = all_read_calls[0].args[1]
            
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'random_potential_duplicate_hashes' ], test_hash_pairs_hex )
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        potentials_search_type = potential_duplicates_search_context.GetDupeSearchType()
        pixel_duplicates = potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = potential_duplicates_search_context.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), default_file_search_context.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), default_file_search_context.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, default_potentials_search_type )
        self.assertEqual( pixel_duplicates, default_pixel_duplicates )
        self.assertEqual( max_hamming_distance, default_max_hamming_distance )
        
        # get random with params
        
        path = '/manage_file_relationships/get_random_potentials?tag_service_key_1={}&tags_1={}&tag_service_key_2={}&tags_2={}&potentials_search_type={}&pixel_duplicates={}&max_hamming_distance={}'.format(
            test_tag_service_key_1.hex(),
            urllib.parse.quote( json.dumps( test_tags_1 ) ),
            test_tag_service_key_2.hex(),
            urllib.parse.quote( json.dumps( test_tags_2 ) ),
            test_potentials_search_type,
            test_pixel_duplicates,
            test_max_hamming_distance
        )
        
        read_db_side_effect = HF.DBSideEffect()
        read_db_side_effect.AddResult( 'random_potential_duplicate_hashes', test_hashes )
        
        with mock.patch.object( TG.test_controller, 'Read', side_effect = read_db_side_effect ) as read_mock_object:
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
            all_read_calls = read_mock_object.call_args_list
            
            self.assertEqual( len( all_read_calls ), 1 )
            
            self.assertEqual( all_read_calls[0].args[0], 'random_potential_duplicate_hashes' )
            
            potential_duplicates_search_context = all_read_calls[0].args[1]
            
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'random_potential_duplicate_hashes' ], test_hash_pairs_hex )
        
        file_search_context_1 = potential_duplicates_search_context.GetFileSearchContext1()
        file_search_context_2 = potential_duplicates_search_context.GetFileSearchContext2()
        potentials_search_type = potential_duplicates_search_context.GetDupeSearchType()
        pixel_duplicates = potential_duplicates_search_context.GetPixelDupesPreference()
        max_hamming_distance = potential_duplicates_search_context.GetMaxHammingDistance()
        
        self.assertEqual( file_search_context_1.GetSerialisableTuple(), test_file_search_context_1.GetSerialisableTuple() )
        self.assertEqual( file_search_context_2.GetSerialisableTuple(), test_file_search_context_2.GetSerialisableTuple() )
        self.assertEqual( potentials_search_type, test_potentials_search_type )
        self.assertEqual( pixel_duplicates, test_pixel_duplicates )
        self.assertEqual( max_hamming_distance, test_max_hamming_distance )
        
    
    def _test_manage_pages( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'manage_pages' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/manage_pages/get_pages'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        pages = d[ 'pages' ]
        
        self.assertEqual( pages[ 'name' ], 'top pages notebook' )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_pages/focus_page'
        
        page_key = os.urandom( 32 )
        
        request_dict = { 'page_key' : page_key.hex() }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        result = TG.test_controller.GetWrite( 'show_page' ) # a fake hook in the controller handles this
        
        expected_result = [ ( ( page_key, ), {} ) ]
        
        self.assertEqual( result, expected_result )
        
        #
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_pages/refresh_page'
        
        page_key = os.urandom( 32 )
        
        request_dict = { 'page_key' : page_key.hex() }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        result = TG.test_controller.GetWrite( 'refresh_page' ) # a fake hook in the controller handles this
        
        expected_result = [ ( ( page_key, ), {} ) ]
        
        self.assertEqual( result, expected_result )
        
    
    def _test_manage_pages_media_viewers( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'manage_pages' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        # this sucks as a test tbh
        # it would be nice if we had the actual Client GUI, but that's not easy atm so maybe we pull the api generating code out of there and test that separately or whatever with fake UI objects
        
        expected_response = [ 1, 2, 3 ]
        
        with mock.patch.object( TG.test_controller.gui, 'GetMediaViewersAPIInfo', return_value = expected_response ):
            
            path = '/manage_pages/get_media_viewers'
            
            connection.request( 'GET', path, headers = headers )
            
            response = connection.getresponse()
            
            data = response.read()
            
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        media_viewers = d[ 'media_viewers' ]
        
        self.assertEqual( media_viewers, expected_response )
        
    
    def _test_manage_services( self, connection, set_up_permissions ):
        
        # this stuff is super dependent on the db requests, which aren't tested in this class, but we can do the arg parsing and wrapper
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        default_location_context = ClientLocation.LocationContext.STATICCreateSimple( CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY )
        
        # get pending counts
        
        db_response = {
            bytes.fromhex( 'ae91919b0ea95c9e636f877f57a69728403b65098238c1a121e5ebf85df3b87e' ) :  {
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS : 11564,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS : 5,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS : 2,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS : 0,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS : 0
            },
            bytes.fromhex( '3902aabc3c4c89d1b821eaa9c011be3047424fd2f0c086346e84794e08e136b0' ) :  {
                HC.SERVICE_INFO_NUM_PENDING_MAPPINGS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_MAPPINGS : 0,
                HC.SERVICE_INFO_NUM_PENDING_TAG_SIBLINGS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_SIBLINGS : 0,
                HC.SERVICE_INFO_NUM_PENDING_TAG_PARENTS : 0,
                HC.SERVICE_INFO_NUM_PETITIONED_TAG_PARENTS : 0
            },
            bytes.fromhex( 'e06e1ae35e692d9fe2b83cde1510a11ecf495f51910d580681cd60e6f21fde73' ) : {
                HC.SERVICE_INFO_NUM_PENDING_FILES : 2,
                HC.SERVICE_INFO_NUM_PETITIONED_FILES : 0
            }
        }
        
        expected_response = {
            "pending_counts" : {
                "ae91919b0ea95c9e636f877f57a69728403b65098238c1a121e5ebf85df3b87e" :  {
                    "pending_tag_mappings" : 11564,
                    "petitioned_tag_mappings" : 5,
                    "pending_tag_siblings" : 2,
                    "petitioned_tag_siblings" : 0,
                    "pending_tag_parents" : 0,
                    "petitioned_tag_parents" : 0
                },
                "3902aabc3c4c89d1b821eaa9c011be3047424fd2f0c086346e84794e08e136b0" :  {
                    "pending_tag_mappings" : 0,
                    "petitioned_tag_mappings" : 0,
                    "pending_tag_siblings" : 0,
                    "petitioned_tag_siblings" : 0,
                    "pending_tag_parents" : 0,
                    "petitioned_tag_parents" : 0
                },
                "e06e1ae35e692d9fe2b83cde1510a11ecf495f51910d580681cd60e6f21fde73" : {
                    "pending_files" : 2,
                    "petitioned_files" : 0
                }
            }
        }
        
        TG.test_controller.SetRead( 'nums_pending', db_response )
        
        path = '/manage_services/get_pending_counts'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'pending_counts' ], expected_response[ 'pending_counts' ] )
        
        #
        
        is_already_running = False
        is_big_problem = False
        magic_results_dict = {}
        
        def IsCurrentlyUploadingPending( *args ):
            
            magic_results_dict[ 'a' ] = True
            
            return is_already_running
            
        
        CG.client_controller.IsCurrentlyUploadingPending = IsCurrentlyUploadingPending
        
        def UploadPending( *args ):
            
            magic_results_dict[ 'b' ] = True
            
            return not is_big_problem
            
        
        CG.client_controller.UploadPending = UploadPending
        
        headers = { 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ], 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/manage_services/commit_pending'
        
        body_dict = { 'service_key' : TG.test_controller.example_file_repo_service_key_1.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( magic_results_dict, { 'a' : True, 'b' : True } )
        
        #
        
        is_already_running = True
        is_big_problem = False
        magic_results_dict = {}
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 409 )
        
        self.assertEqual( magic_results_dict, { 'a' : True } )
        
        #
        
        is_already_running = False
        is_big_problem = True
        magic_results_dict = {}
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 422 )
        
        self.assertEqual( magic_results_dict, { 'a' : True, 'b' : True } )
        
        #
        
        TG.test_controller.ClearWrites( 'delete_pending' )
        
        headers = { 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ], 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/manage_services/forget_pending'
        
        body_dict = { 'service_key' : TG.test_controller.example_file_repo_service_key_1.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_key, ), kwargs ) ] = TG.test_controller.GetWrite( 'delete_pending' )
        
        self.assertEqual( service_key, TG.test_controller.example_file_repo_service_key_1 )
        
    
    def _test_options( self, connection, set_up_permissions ):
        
        # first fail
        
        api_permissions = set_up_permissions[ 'add_urls' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/manage_database/get_client_options'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # now good
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/manage_database/get_client_options'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        text = str( data, 'utf-8' )
        
        d = json.loads( text )
        
        self.assertIn( 'old_options', d )
        self.assertIn( 'options', d )
        
    
    def _test_search_files( self, connection, set_up_permissions ):
        
        hash_ids = [ 1, 2, 3, 4, 5, 10, 15, 16, 17, 18, 19, 20, 21, 25, 100, 101, 150 ]
        
        # search files failed tag permission
        
        api_permissions = set_up_permissions[ 'search_green_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino' ]
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # search files
        
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = { 'file_ids' : list( sample_hash_ids ) }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetLocationContext().current_service_keys, { CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY } )
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( file_search_context.GetTagContext().include_current_tags, True )
        self.assertEqual( file_search_context.GetTagContext().include_pending_tags, True )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_DESC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # include current/pending
        
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&include_current_tags=false'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = { 'file_ids' : list( sample_hash_ids ) }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( file_search_context.GetTagContext().include_current_tags, False )
        self.assertEqual( file_search_context.GetTagContext().include_pending_tags, True )
        
        path = '/get_files/search_files?tags={}&include_pending_tags=false'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = { 'file_ids' : list( sample_hash_ids ) }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( file_search_context.GetTagContext().include_current_tags, True )
        self.assertEqual( file_search_context.GetTagContext().include_pending_tags, False )
        
        # search files and get hashes
        
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        hash_ids_to_hashes = { hash_id : os.urandom( 32 ) for hash_id in sample_hash_ids }
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', hash_ids_to_hashes )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&return_hashes=true'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_hashes_set = { hash.hex() for hash in hash_ids_to_hashes.values() }
        
        self.assertEqual( set( d[ 'hashes' ] ), expected_hashes_set )
        
        self.assertIn( 'file_ids', d )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetLocationContext().current_service_keys, { CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY } )
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_DESC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'hash_ids_to_hashes' )
        
        hash_ids = kwargs[ 'hash_ids' ]
        
        self.assertEqual( set( hash_ids ), sample_hash_ids )
        
        self.assertEqual( set( hash_ids ), set( d[ 'file_ids' ] ) )
        
        # search files and only get hashes
        
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        hash_ids_to_hashes = { hash_id : os.urandom( 32 ) for hash_id in sample_hash_ids }
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', hash_ids_to_hashes )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&return_hashes=true&return_file_ids=false'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_hashes_set = { hash.hex() for hash in hash_ids_to_hashes.values() }
        
        self.assertEqual( set( d[ 'hashes' ] ), expected_hashes_set )
        
        self.assertNotIn( 'file_ids', d )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetLocationContext().current_service_keys, { CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY } )
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_DESC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'hash_ids_to_hashes' )
        
        hash_ids = kwargs[ 'hash_ids' ]
        
        self.assertEqual( set( hash_ids ), sample_hash_ids )
        
        # sort
        
        # this just tests if it parses, we don't have a full test for read params yet
        
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}'.format( urllib.parse.quote( json.dumps( tags ) ), CC.SORT_FILES_BY_FRAMERATE )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetLocationContext().current_service_keys, { CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY } )
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_FRAMERATE ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_DESC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # sort
        
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}&file_sort_asc={}'.format( urllib.parse.quote( json.dumps( tags ) ), CC.SORT_FILES_BY_FRAMERATE, 'true' )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetLocationContext().current_service_keys, { CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY } )
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_FRAMERATE ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_ASC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # file domain
        
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}&file_sort_asc={}&file_service_key={}'.format(
            urllib.parse.quote( json.dumps( tags ) ),
            CC.SORT_FILES_BY_FRAMERATE,
            'true',
            CC.TRASH_SERVICE_KEY.hex()
        )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetLocationContext().current_service_keys, { CC.TRASH_SERVICE_KEY } )
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_FRAMERATE ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_ASC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # file and tag domain
        
        TG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}&file_sort_asc={}&file_service_key={}&tag_service_key={}'.format(
            urllib.parse.quote( json.dumps( tags ) ),
            CC.SORT_FILES_BY_FRAMERATE,
            'true',
            CC.TRASH_SERVICE_KEY.hex(),
            CC.COMBINED_TAG_SERVICE_KEY.hex()
        )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = TG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetLocationContext().current_service_keys, { CC.TRASH_SERVICE_KEY } )
        self.assertEqual( file_search_context.GetTagContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearchPredicate.Predicate( ClientSearchPredicate.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_FRAMERATE ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_ASC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # file and tag domain
        
        # this just tests if it parses, we don't have a full test for read params yet
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}&file_sort_asc={}&file_service_key={}&tag_service_key={}'.format(
            urllib.parse.quote( json.dumps( tags ) ),
            CC.SORT_FILES_BY_FRAMERATE,
            'true',
            CC.COMBINED_FILE_SERVICE_KEY.hex(),
            CC.COMBINED_TAG_SERVICE_KEY.hex()
        )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 400 )
        
        # empty
        
        sample_hash_ids = set( random.sample( list( hash_ids ), 3 ) )
        
        # set it, just to check we aren't ever asking
        TG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = []
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        d = json.loads( text )
        
        self.assertEqual( d[ 'file_ids' ], [] )
        
        self.assertEqual( response.status, 200 )
        
    
    def _test_search_files_predicate_parsing( self, connection, set_up_permissions ):
        
        # some file search param parsing
        
        class PretendRequest( object ):
            
            pass
            
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = {}
        pretend_request.client_api_permissions = set_up_permissions[ 'everything' ]
        
        predicates = ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
        
        self.assertEqual( predicates, [] )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ '-green' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
            
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green*' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
            
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ '*r:green' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
            
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green', '-kino' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_TAG, value = 'kino', inclusive = False ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green', 'system:archive' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green', [ 'red', 'blue' ], 'system:archive' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_TAG, value = 'green' ) )
        
        expected_predicates.append(
            ClientSearchPredicate.Predicate(
                predicate_type = ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER,
                value = [
                    ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_TAG, value = 'red' ),
                    ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_TAG, value = 'blue' )
                ]
            )
        )
        
        expected_predicates.append( ClientSearchPredicate.Predicate( predicate_type = ClientSearchPredicate.PREDICATE_TYPE_SYSTEM_ARCHIVE ) )
        
        self.assertEqual( { pred for pred in predicates if pred.GetType() != ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER }, { pred for pred in expected_predicates if pred.GetType() != ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER } )
        self.assertEqual( { frozenset( pred.GetValue() ) for pred in predicates if pred.GetType() == ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER }, { frozenset( pred.GetValue() ) for pred in expected_predicates if pred.GetType() == ClientSearchPredicate.PREDICATE_TYPE_OR_CONTAINER } )
        
        #
        
        # bad tag
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'bad_tag:' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'everything' ]
        
        with self.assertRaises( HydrusExceptions.BadRequestException ):
            
            ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
            
        
        # bad negated
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ '-bad_tag:' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'everything' ]
        
        with self.assertRaises( HydrusExceptions.BadRequestException ):
            
            ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
            
        
        # bad system pred
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'system:bad_system_pred' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'everything' ]
        
        with self.assertRaises( HydrusExceptions.BadRequestException ):
            
            ClientLocalServerCore.ParseClientAPISearchPredicates( pretend_request )
            
        
    
    def _test_file_hashes( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        md5_hash = bytes.fromhex( 'ec5c5a4d7da4be154597e283f0b6663c' )
        sha256_hash = bytes.fromhex( '2a0174970defa6f147f2eabba829c5b05aba1f1aea8b978611a07b7bb9cf9399' )
        
        source_to_dest = { md5_hash : sha256_hash }
        
        TG.test_controller.SetRead( 'file_hashes', source_to_dest )
        
        path = '/get_files/file_hashes?source_hash_type=md5&desired_hash_type=sha256&hash={}'.format( md5_hash.hex() )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = {
            'hashes' : {
                md5_hash.hex() : sha256_hash.hex()
            }
        }
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
    
    def _test_file_metadata( self, connection, set_up_permissions ):
        
        # test file metadata
        
        api_permissions = set_up_permissions[ 'search_green_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        file_ids_to_hashes = { i : os.urandom( 32 ) for i in range( 20 ) }
        
        metadata = []
        
        for ( file_id, hash ) in file_ids_to_hashes.items():
            
            if file_id == 0 or file_id >= 4:
                
                continue
                
            
            metadata_row = { 'file_id' : file_id, 'hash' : hash.hex() }
            
            metadata.append( metadata_row )
            
        
        expected_identifier_result = { 'metadata' : metadata, 'services' : GetExampleServicesDict() }
        
        wash_example_json_response( expected_identifier_result )
        
        media_results = []
        file_info_managers = []
        
        urls = { "https://gelbooru.com/index.php?page=post&s=view&id=4841557", "https://img2.gelbooru.com/images/80/c8/80c8646b4a49395fb36c805f316c49a9.jpg" }
        
        sorted_urls = sorted( urls )
        
        random_file_service_hex_current = TG.test_controller.example_file_repo_service_key_1
        random_file_service_hex_deleted = TG.test_controller.example_file_repo_service_key_2
        
        current_import_timestamp_ms = 500127
        ipfs_import_timestamp_ms = 123456126
        previously_imported_timestamp_ms = 300125
        deleted_deleted_timestamp_ms = 450124
        file_modified_timestamp_ms = 20123
        
        done_a_multihash = False
        
        for ( file_id, hash ) in file_ids_to_hashes.items():
            
            if file_id == 0 or file_id >= 4:
                
                continue
                
            
            size = random.randint( 8192, 20 * 1048576 )
            mime = random.choice( [ HC.IMAGE_JPEG, HC.VIDEO_WEBM, HC.APPLICATION_PDF ] )
            width = random.randint( 200, 4096 )
            height = random.randint( 200, 4096 )
            duration_ms = random.choice( [ 220, 16.66667, None ] )
            has_audio = random.choice( [ True, False ] )
            
            file_info_manager = ClientMediaManagers.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration_ms = duration_ms, has_audio = has_audio )
            
            file_info_manager.has_exif = True
            file_info_manager.has_icc_profile = True
            
            file_info_manager.blurhash = 'UBECh1xtFg-X-qxvxZ$*4mD%n3s*M_I9IVNG'
            file_info_manager.pixel_hash = os.urandom( 32 )
            
            file_info_managers.append( file_info_manager )
            
            service_keys_to_statuses_to_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue_eyes', 'blonde_hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit' ] } }
            service_keys_to_statuses_to_display_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue eyes', 'blonde hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit', 'clothing' ] } }
            
            service_keys_to_filenames = {}
            
            current_to_timestamps_ms = { random_file_service_hex_current : current_import_timestamp_ms }
            
            if not done_a_multihash:
                
                done_a_multihash = True
                
                current_to_timestamps_ms[ TG.test_controller.example_ipfs_service_key ] = ipfs_import_timestamp_ms
                
                service_keys_to_filenames[ TG.test_controller.example_ipfs_service_key ] = 'QmReHtaET3dsgh7ho5NVyHb5U13UgJoGipSWbZsnuuM8tb'
                
            
            tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
            
            times_manager = ClientMediaManagers.TimesManager()
            
            times_manager.SetFileModifiedTimestampMS( file_modified_timestamp_ms )
            times_manager.SetImportedTimestampsMS( current_to_timestamps_ms )
            
            deleted_to_timestamps_ms = { random_file_service_hex_deleted : deleted_deleted_timestamp_ms }
            deleted_to_previously_imported_timestamp_ms = { random_file_service_hex_deleted : previously_imported_timestamp_ms }
            
            times_manager.SetDeletedTimestampsMS( deleted_to_timestamps_ms )
            times_manager.SetPreviouslyImportedTimestampsMS( deleted_to_previously_imported_timestamp_ms )
            
            locations_manager = ClientMediaManagers.LocationsManager(
                set( current_to_timestamps_ms.keys() ),
                set( deleted_to_timestamps_ms.keys() ),
                set(),
                set(),
                times_manager,
                inbox = False,
                urls = urls,
                service_keys_to_filenames = service_keys_to_filenames
            )
            
            ratings_dict = {}
            
            if random.random() > 0.6:
                
                ratings_dict[ TG.test_controller.example_like_rating_service_key ] = 0.0 if random.random() < 0 else 1.0
                
            
            if random.random() > 0.6:
                
                ratings_dict[ TG.test_controller.example_numerical_rating_service_key ] = random.random()
                
            
            if random.random() > 0.6:
                
                ratings_dict[ TG.test_controller.example_incdec_rating_service_key ] = int( random.random() * 16 )
                
            
            if random.random() > 0.8:
                
                file_info_manager.original_mime = HC.IMAGE_PNG
                
            
            ratings_manager = ClientMediaManagers.RatingsManager( {} )
            notes_manager = ClientMediaManagers.NotesManager( { 'note' : 'hello', 'note2' : 'hello2' } )
            
            view_rows = [
                ( CC.CANVAS_MEDIA_VIEWER, HydrusTime.GetNowMS() - 50000, 5, 310567 ),
                ( CC.CANVAS_PREVIEW, HydrusTime.GetNowMS() - 60000, 17, 662567 )
            ]
            
            file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager( times_manager, view_rows )
            
            media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
            
            media_results.append( media_result )
            
        
        metadata = []
        detailed_known_urls_metadata = []
        with_notes_metadata = []
        only_return_basic_information_metadata = []
        only_return_basic_information_metadata_but_blurhash_too = []
        
        services_manager = CG.client_controller.services_manager
        
        for media_result in media_results:
            
            file_info_manager = media_result.GetFileInfoManager()
            
            metadata_row = {
                'file_id' : file_info_manager.hash_id,
                'hash' : file_info_manager.hash.hex(),
                'size' : file_info_manager.size,
                'mime' : HC.mime_mimetype_string_lookup[ file_info_manager.mime ],
                'filetype_human' : HC.mime_string_lookup[ file_info_manager.mime ],
                'filetype_enum' : file_info_manager.mime,
                'ext' : HC.mime_ext_lookup[ file_info_manager.mime ],
                'width' : file_info_manager.width,
                'height' : file_info_manager.height,
                'duration' : file_info_manager.duration_ms,
                'has_audio' : file_info_manager.has_audio,
                'num_frames' : file_info_manager.num_frames,
                'num_words' : file_info_manager.num_words
            }
            
            filetype_forced = file_info_manager.FiletypeIsForced()
            
            metadata_row[ 'filetype_forced' ] = filetype_forced
            
            if filetype_forced:
                
                metadata_row[ 'original_mime' ] = HC.mime_mimetype_string_lookup[ file_info_manager.original_mime ]
                
            
            only_return_basic_information_metadata.append( dict( metadata_row ) )
            
            metadata_row[ 'blurhash' ] = file_info_manager.blurhash
            
            only_return_basic_information_metadata_but_blurhash_too.append( dict( metadata_row ) )
            
            if file_info_manager.mime in HC.MIMES_WITH_THUMBNAILS:
                
                bounding_dimensions = TG.test_controller.options[ 'thumbnail_dimensions' ]
                thumbnail_scale_type = TG.test_controller.new_options.GetInteger( 'thumbnail_scale_type' )
                thumbnail_dpr_percent = CG.client_controller.new_options.GetInteger( 'thumbnail_dpr_percent' )
                
                ( thumbnail_expected_width, thumbnail_expected_height ) = HydrusImageHandling.GetThumbnailResolution( ( file_info_manager.width, file_info_manager.height ), bounding_dimensions, thumbnail_scale_type, thumbnail_dpr_percent )
                
                metadata_row[ 'thumbnail_width' ] = thumbnail_expected_width
                metadata_row[ 'thumbnail_height' ] = thumbnail_expected_height
                
            
            metadata_row.update( {
                'file_services' : {
                    'current' : {
                        random_file_service_hex_current.hex() : {
                            'time_imported' : HydrusTime.SecondiseMS( current_import_timestamp_ms ),
                            'name' : TG.test_controller.services_manager.GetName( random_file_service_hex_current ),
                            'type' : TG.test_controller.services_manager.GetServiceType( random_file_service_hex_current ),
                            'type_pretty' : HC.service_string_lookup[ TG.test_controller.services_manager.GetServiceType( random_file_service_hex_current ) ]
                        }
                    },
                    'deleted' : {
                        random_file_service_hex_deleted.hex() : {
                            'time_deleted' : HydrusTime.SecondiseMS( deleted_deleted_timestamp_ms ),
                            'time_imported' : HydrusTime.SecondiseMS( previously_imported_timestamp_ms ),
                            'name' : TG.test_controller.services_manager.GetName( random_file_service_hex_deleted ),
                            'type' : TG.test_controller.services_manager.GetServiceType( random_file_service_hex_deleted ),
                            'type_pretty' : HC.service_string_lookup[ TG.test_controller.services_manager.GetServiceType( random_file_service_hex_deleted ) ]
                        }
                    }
                },
                'ipfs_multihashes' : {},
                'time_modified' : HydrusTime.SecondiseMS( file_modified_timestamp_ms ),
                'time_modified_details' : {
                    'local' : HydrusTime.SecondiseMS( file_modified_timestamp_ms )
                },
                'is_inbox' : False,
                'is_local' : False,
                'is_trashed' : False,
                'is_deleted' : False,
                'has_transparency' : False,
                'has_exif' : True,
                'has_human_readable_embedded_metadata' : False,
                'has_icc_profile' : True,
                'known_urls' : list( sorted_urls ),
                'pixel_hash' : file_info_manager.pixel_hash.hex()
            } )
            
            locations_manager = media_result.GetLocationsManager()
            
            if len( locations_manager.GetServiceFilenames() ) > 0:
                
                for ( i_s_k, multihash ) in locations_manager.GetServiceFilenames().items():
                    
                    metadata_row[ 'file_services' ][ 'current' ][ i_s_k.hex() ] = {
                        'time_imported' : HydrusTime.SecondiseMS( ipfs_import_timestamp_ms ),
                        'name' : TG.test_controller.services_manager.GetName( i_s_k ),
                        'type' : TG.test_controller.services_manager.GetServiceType( i_s_k ),
                        'type_pretty' : HC.service_string_lookup[ TG.test_controller.services_manager.GetServiceType( i_s_k ) ]
                    }
                    
                    metadata_row[ 'ipfs_multihashes' ][ i_s_k.hex() ] = multihash
                    
                
            
            ratings_manager = media_result.GetRatingsManager()
            
            ratings_dict = {}
            
            rating_service_keys = services_manager.GetServiceKeys( HC.RATINGS_SERVICES )
            
            for rating_service_key in rating_service_keys:
                
                ratings_dict[ rating_service_key.hex() ] = ratings_manager.GetRatingForAPI( rating_service_key )
                
            
            metadata_row[ 'ratings' ] = ratings_dict
            
            tags_manager = media_result.GetTagsManager()
            
            tags_dict = {}
            
            tag_service_keys = services_manager.GetServiceKeys( HC.ALL_TAG_SERVICES )
            service_keys_to_types = { service.GetServiceKey() : service.GetServiceType() for service in services_manager.GetServices() }
            service_keys_to_names = services_manager.GetServiceKeysToNames()
            
            for tag_service_key in tag_service_keys:
                
                storage_statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, ClientTags.TAG_DISPLAY_STORAGE )
                
                storage_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusText.HumanTextSortKey ) for ( status, tags ) in storage_statuses_to_tags.items() if len( tags ) > 0 }
                
                display_statuses_to_tags = tags_manager.GetStatusesToTags( tag_service_key, ClientTags.TAG_DISPLAY_DISPLAY_ACTUAL )
                
                display_tags_json_serialisable = { str( status ) : sorted( tags, key = HydrusText.HumanTextSortKey ) for ( status, tags ) in display_statuses_to_tags.items() if len( tags ) > 0 }
                
                tags_dict_object = {
                    'name' : service_keys_to_names[ tag_service_key ],
                    'type' : service_keys_to_types[ tag_service_key ],
                    'type_pretty' : HC.service_string_lookup[ service_keys_to_types[ tag_service_key ] ],
                    'storage_tags' : storage_tags_json_serialisable,
                    'display_tags' : display_tags_json_serialisable
                }
                
                tags_dict[ tag_service_key.hex() ] = tags_dict_object
                
            
            metadata_row[ 'tags' ] = tags_dict
            
            times_manager = media_result.GetTimesManager()
            fvsm = media_result.GetFileViewingStatsManager()
            
            file_viewing_stats_list = []
            
            for canvas_type in [
                CC.CANVAS_MEDIA_VIEWER,
                CC.CANVAS_PREVIEW,
                CC.CANVAS_CLIENT_API
            ]:
                
                views = fvsm.GetViews( canvas_type )
                viewtime = HydrusTime.SecondiseMSFloat( fvsm.GetViewtimeMS( canvas_type ) )
                last_viewed_timestamp = HydrusTime.SecondiseMSFloat( times_manager.GetLastViewedTimestampMS( canvas_type ) )
                
                json_object = {
                    'canvas_type' : canvas_type,
                    'canvas_type_pretty' : CC.canvas_type_str_lookup[ canvas_type ],
                    'views' : views,
                    'viewtime' : viewtime,
                    'last_viewed_timestamp' : last_viewed_timestamp
                }
                
                file_viewing_stats_list.append( json_object )
                
            
            metadata_row[ 'file_viewing_statistics' ] = file_viewing_stats_list
            
            metadata.append( metadata_row )
            
            detailed_known_urls_metadata_row = dict( metadata_row )
            
            detailed_known_urls_metadata_row[ 'detailed_known_urls' ] = [
                {'normalised_url' : 'https://gelbooru.com/index.php?id=4841557&page=post&s=view', 'url_type' : 0, 'url_type_string' : 'post url', 'match_name' : 'gelbooru file page', 'can_parse' : True},
                {'normalised_url' : 'https://img2.gelbooru.com/images/80/c8/80c8646b4a49395fb36c805f316c49a9.jpg', 'url_type' : 5, 'url_type_string' : 'unknown url', 'match_name' : 'unknown url', 'can_parse' : False, 'cannot_parse_reason' : 'unknown url class'}
            ]
            
            detailed_known_urls_metadata.append( detailed_known_urls_metadata_row )
            
            with_notes_metadata_row = dict( metadata_row )
            
            with_notes_metadata_row[ 'notes' ] = media_result.GetNotesManager().GetNamesToNotes()
            
            with_notes_metadata.append( with_notes_metadata_row )
            
        
        expected_metadata_result = { 'metadata' : metadata, 'services' : GetExampleServicesDict() }
        expected_detailed_known_urls_metadata_result = { 'metadata' : detailed_known_urls_metadata, 'services' : GetExampleServicesDict() }
        expected_notes_metadata_result = { 'metadata' : with_notes_metadata, 'services' : GetExampleServicesDict() }
        expected_only_return_basic_information_result = { 'metadata' : only_return_basic_information_metadata, 'services' : GetExampleServicesDict() }
        expected_only_return_basic_information_but_blurhash_too_result = { 'metadata' : only_return_basic_information_metadata_but_blurhash_too, 'services' : GetExampleServicesDict() }
        
        wash_example_json_response( expected_metadata_result )
        wash_example_json_response( expected_detailed_known_urls_metadata_result )
        wash_example_json_response( expected_notes_metadata_result )
        wash_example_json_response( expected_only_return_basic_information_result )
        wash_example_json_response( expected_only_return_basic_information_but_blurhash_too_result )
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', file_ids_to_hashes )
        TG.test_controller.SetRead( 'media_results', media_results )
        TG.test_controller.SetRead( 'media_results_from_ids', media_results )
        TG.test_controller.SetRead( 'file_info_managers', file_info_managers )
        TG.test_controller.SetRead( 'file_info_managers_from_ids', file_info_managers )
        
        api_permissions.SetLastSearchResults( [ 1, 2, 3, 4, 5, 6 ] )
        
        # fail on non-permitted files
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { k : v for ( k, v ) in file_ids_to_hashes.items() if k in [ 1, 2, 3, 7 ] } )
        
        path = '/get_files/file_metadata?file_ids={}&only_return_identifiers=true'.format( urllib.parse.quote( json.dumps( [ 1, 2, 3, 7 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # fails on hashes even if the hashes are 'good'
        
        path = '/get_files/file_metadata?hashes={}&only_return_identifiers=true'.format( urllib.parse.quote( json.dumps( [ hash.hex() for hash in file_ids_to_hashes.values() ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # identifiers from file_ids
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { k : v for ( k, v ) in file_ids_to_hashes.items() if k in [ 1, 2, 3 ] } )
        
        path = '/get_files/file_metadata?file_ids={}&only_return_identifiers=true'.format( urllib.parse.quote( json.dumps( [ 1, 2, 3 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_identifier_result )
        
        # basic metadata from file_ids
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { k : v for ( k, v ) in file_ids_to_hashes.items() if k in [ 1, 2, 3 ] } )
        
        path = '/get_files/file_metadata?file_ids={}&only_return_basic_information=true'.format( urllib.parse.quote( json.dumps( [ 1, 2, 3 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_only_return_basic_information_result )
        
        # basic metadata with blurhash
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { k : v for ( k, v ) in file_ids_to_hashes.items() if k in [ 1, 2, 3 ] } )
        
        path = '/get_files/file_metadata?file_ids={}&only_return_basic_information=true&include_blurhash=true'.format( urllib.parse.quote( json.dumps( [ 1, 2, 3 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_only_return_basic_information_but_blurhash_too_result )
        
        # same but diff order
        
        expected_order = [ 3, 1, 2 ]
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { k : v for ( k, v ) in file_ids_to_hashes.items() if k in [ 1, 2, 3 ] } )
        
        path = '/get_files/file_metadata?file_ids={}&only_return_basic_information=true'.format( urllib.parse.quote( json.dumps( expected_order ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = { 'metadata' : list( expected_only_return_basic_information_result[ 'metadata' ] ), 'services' : GetExampleServicesDict() }
        
        expected_result[ 'metadata' ].sort( key = lambda basic: expected_order.index( basic[ 'file_id' ] ) )
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # metadata from file_ids
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { k : v for ( k, v ) in file_ids_to_hashes.items() if k in [ 1, 2, 3 ] } )
        
        path = '/get_files/file_metadata?file_ids={}'.format( urllib.parse.quote( json.dumps( [ 1, 2, 3 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        # quick print-inspect on what went wrong
        '''
        m = d[ 'metadata' ]
        m_e = expected_metadata_result[ 'metadata' ]
        
        for ( i, file_post ) in enumerate( m ):
            
            file_post_e = m_e[ i ]
            
            for j in file_post.keys():
                
                HydrusData.Print( ( j, file_post[j] ) )
                HydrusData.Print( ( j, file_post_e[j] ) )
                
            
        
        self.maxDiff = None
        '''
        
        for ( row_a, row_b ) in zip( d[ 'metadata' ], expected_metadata_result[ 'metadata' ] ):
            
            self.assertEqual( set( row_a.keys() ), set( row_b.keys() ) )
            
            for key in list( row_a.keys() ):
                
                self.assertEqual( row_a[ key ], row_b[ key ] )
                
            
        
        # same but diff order
        
        expected_order = [ 3, 1, 2 ]
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { k : v for ( k, v ) in file_ids_to_hashes.items() if k in [ 1, 2, 3 ] } )
        
        path = '/get_files/file_metadata?file_ids={}'.format( urllib.parse.quote( json.dumps( expected_order ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        # quick print-inspect on what went wrong
        '''
        m = d[ 'metadata' ]
        m_e = expected_metadata_result[ 'metadata' ]
        
        for ( i, file_post ) in enumerate( m ):
            
            file_post_e = m_e[ i ]
            
            for j in file_post.keys():
                
                HydrusData.Print( ( j, file_post[j] ) )
                HydrusData.Print( ( j, file_post_e[j] ) )
                
            
        
        self.maxDiff = None
        '''
        
        expected_result = { 'metadata' : list( expected_metadata_result[ 'metadata' ] ), 'services' : GetExampleServicesDict() }
        
        expected_result[ 'metadata' ].sort( key = lambda basic: expected_order.index( basic[ 'file_id' ] ) )
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        for ( row_a, row_b ) in zip( d[ 'metadata' ], expected_result[ 'metadata' ] ):
            
            self.assertEqual( set( row_a.keys() ), set( row_b.keys() ) )
            
            for key in list( row_a.keys() ):
                
                self.assertEqual( row_a[ key ], row_b[ key ] )
                
            
        
        # metadata from file_ids, with milliseconds
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', { k : v for ( k, v ) in file_ids_to_hashes.items() if k in [ 1, 2, 3 ] } )
        
        path = '/get_files/file_metadata?file_ids={}&include_milliseconds=true'.format( urllib.parse.quote( json.dumps( [ 1, 2, 3 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        for file_row in d[ 'metadata' ]:
            
            self.assertEqual( file_row[ 'time_modified' ], HydrusTime.SecondiseMSFloat( file_modified_timestamp_ms ) )
            
        
        # now from hashes
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        # identifiers from hashes
        
        path = '/get_files/file_metadata?hashes={}&only_return_identifiers=true'.format( urllib.parse.quote( json.dumps( [ file_ids_to_hashes[ hash_id ].hex() for hash_id in [ 1, 2, 3 ] ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_identifier_result )
        
        # same but diff order
        
        expected_order = [ 3, 1, 2 ]
        
        path = '/get_files/file_metadata?hashes={}&only_return_identifiers=true'.format( urllib.parse.quote( json.dumps( [ file_ids_to_hashes[ hash_id ].hex() for hash_id in expected_order ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = { 'metadata' : list( expected_identifier_result[ 'metadata' ] ), 'services' : GetExampleServicesDict() }
        
        expected_result[ 'metadata' ].sort( key = lambda basic: expected_order.index( basic[ 'file_id' ] ) )
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # basic metadata from hashes
        
        path = '/get_files/file_metadata?hashes={}&only_return_basic_information=true'.format( urllib.parse.quote( json.dumps( [ file_ids_to_hashes[ hash_id ].hex() for hash_id in [ 1, 2, 3 ] ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_only_return_basic_information_result )
        
        # same but diff order
        
        expected_order = [ 3, 1, 2 ]
        
        path = '/get_files/file_metadata?hashes={}&only_return_basic_information=true'.format( urllib.parse.quote( json.dumps( [ file_ids_to_hashes[ hash_id ].hex() for hash_id in expected_order ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = { 'metadata' : list( expected_only_return_basic_information_result[ 'metadata' ] ), 'services' : GetExampleServicesDict() }
        
        expected_result[ 'metadata' ].sort( key = lambda basic: expected_order.index( basic[ 'file_id' ] ) )
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # metadata from hashes
        
        path = '/get_files/file_metadata?hashes={}'.format( urllib.parse.quote( json.dumps( [ file_ids_to_hashes[ hash_id ].hex() for hash_id in [ 1, 2, 3 ] ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_metadata_result )
        
        # same but diff order
        
        path = '/get_files/file_metadata?hashes={}'.format( urllib.parse.quote( json.dumps( [ file_ids_to_hashes[ hash_id ].hex() for hash_id in expected_order ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_result = { 'metadata' : list( expected_metadata_result[ 'metadata' ] ), 'services' : GetExampleServicesDict() }
        
        expected_result[ 'metadata' ].sort( key = lambda basic: expected_order.index( basic[ 'file_id' ] ) )
        
        wash_example_json_response( expected_result )
        
        self.assertEqual( d, expected_result )
        
        # fails on borked hashes
        
        path = '/get_files/file_metadata?hashes={}'.format( urllib.parse.quote( json.dumps( [ 'deadbeef' ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 )
        
        # metadata from hashes with detailed url info
        
        path = '/get_files/file_metadata?hashes={}&detailed_url_information=true'.format( urllib.parse.quote( json.dumps( [ file_ids_to_hashes[ hash_id ].hex() for hash_id in [ 1, 2, 3 ] ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_detailed_known_urls_metadata_result )
        
        # metadata from hashes with notes info
        
        path = '/get_files/file_metadata?hashes={}&include_notes=true'.format( urllib.parse.quote( json.dumps( [ file_ids_to_hashes[ hash_id ].hex() for hash_id in [ 1, 2, 3 ] ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_notes_metadata_result )
        
        # failure on missing file_ids
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', HydrusExceptions.DataMissing( 'test missing' ) )
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        path = '/get_files/file_metadata?file_ids={}'.format( urllib.parse.quote( json.dumps( [ 123456 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 404 )
        self.assertIn( 'test missing', text )
        
        # no new file_ids
        
        TG.test_controller.SetRead( 'hash_ids_to_hashes', file_ids_to_hashes )
        TG.test_controller.SetRead( 'media_results_from_ids', media_results )
        
        hashes_in_test = [ mr.GetHash() for mr in media_results ]
        
        novel_hashes = [ os.urandom( 32 ) for i in range( 5 ) ]
        
        hashes_in_test.extend( novel_hashes )
        
        expected_result = {
            'metadata' : expected_metadata_result[ 'metadata' ] + [
                {
                    'hash' : hash.hex(),
                    'file_id' : None
                } for hash in novel_hashes
            ]
        }
        
        random.shuffle( hashes_in_test )
        
        expected_result[ 'metadata' ].sort( key = lambda m_dict: hashes_in_test.index( bytes.fromhex( m_dict[ 'hash' ] ) ) )
        
        wash_example_json_response( expected_result )
        
        path = '/get_files/file_metadata?hashes={}&include_services_object=false'.format( urllib.parse.quote( json.dumps( [ hash.hex() for hash in hashes_in_test ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_result )
        
    
    def _test_get_files( self, connection, set_up_permissions ):
        
        # files and thumbs
        
        file_id = 1
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        hash_hex = hash.hex()
        
        size = 100
        mime = HC.IMAGE_PNG
        width = 20
        height = 20
        duration_ms = None
        
        file_info_manager = ClientMediaManagers.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration_ms = duration_ms )
        
        service_keys_to_statuses_to_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue_eyes', 'blonde_hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit' ] } }
        service_keys_to_statuses_to_display_tags =  { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue eyes', 'blonde hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit', 'clothing' ] } }
        
        tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
        
        times_manager = ClientMediaManagers.TimesManager()
        
        locations_manager = ClientMediaManagers.LocationsManager( { CC.HYDRUS_LOCAL_FILE_STORAGE_SERVICE_KEY, CC.COMBINED_LOCAL_FILE_DOMAINS_SERVICE_KEY, CC.LOCAL_FILE_SERVICE_KEY }, set(), set(), set(), times_manager )
        ratings_manager = ClientMediaManagers.RatingsManager( {} )
        notes_manager = ClientMediaManagers.NotesManager( {} )
        file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager.STATICGenerateEmptyManager( times_manager )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
        TG.test_controller.SetRead( 'media_result', media_result )
        TG.test_controller.SetRead( 'media_results_from_ids', ( media_result, ) )
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        file_path = TG.test_controller.client_files_manager.GetFilePath( hash, HC.IMAGE_PNG, check_file_exists = False )
        
        HydrusPaths.safe_copy2( path, file_path )
        
        thumb_hash = b'\x17\xde\xd6\xee\x1b\xfa\x002\xbdj\xc0w\x92\xce5\xf0\x12~\xfe\x915\xb3\xb3tA\xac\x90F\x95\xc2T\xc5'
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus_small.png' )
        
        thumb_path = TG.test_controller.client_files_manager._GenerateExpectedThumbnailPath( hash )
        
        HydrusPaths.safe_copy2( path, thumb_path )
        
        api_permissions = set_up_permissions[ 'search_green_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        # let's fail first
        
        path = '/get_files/file?file_id={}'.format( 10 )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        #
        
        path = '/get_files/thumbnail?file_id={}'.format( 10 )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        #
        
        path = '/get_files/file?hash={}'.format( hash_hex )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        #
        
        path = '/get_files/thumbnail?hash={}'.format( hash_hex )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # now succeed
        
        path = '/get_files/file?file_id={}'.format( 1 )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( hashlib.sha256( data ).digest(), hash )
        
        self.assertIn( 'inline', response.headers[ 'Content-Disposition' ] )
        
        # succeed with attachment
        
        path = '/get_files/file?file_id={}&download=true'.format( 1 )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( hashlib.sha256( data ).digest(), hash )
        
        self.assertIn( 'attachment', response.headers[ 'Content-Disposition' ] )
        
        # range request
        
        path = '/get_files/file?file_id={}'.format( 1 )
        
        partial_headers = dict( headers )
        partial_headers[ 'Range' ] = 'bytes=100-199'
        
        connection.request( 'GET', path, headers = partial_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 206 )
        
        with open( file_path, 'rb' ) as f:
            
            f.seek( 100 )
            
            actual_data = f.read( 100 )
            
        
        self.assertEqual( data, actual_data )
        
        # n onwards range request
        
        path = '/get_files/file?file_id={}'.format( 1 )
        
        partial_headers = dict( headers )
        partial_headers[ 'Range' ] = 'bytes=100-'
        
        connection.request( 'GET', path, headers = partial_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 206 )
        
        with open( file_path, 'rb' ) as f:
            
            f.seek( 100 )
            
            actual_data = f.read()
            
        
        self.assertEqual( data, actual_data )
        
        # last n onwards range request
        
        path = '/get_files/file?file_id={}'.format( 1 )
        
        partial_headers = dict( headers )
        partial_headers[ 'Range' ] = 'bytes=-100'
        
        connection.request( 'GET', path, headers = partial_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 206 )
        
        with open( file_path, 'rb' ) as f:
            
            actual_data = f.read()[-100:]
            
        
        self.assertEqual( data, actual_data )
        
        # invalid range request
        
        path = '/get_files/file?file_id={}'.format( 1 )
        
        partial_headers = dict( headers )
        partial_headers[ 'Range' ] = 'bytes=200-199'
        
        connection.request( 'GET', path, headers = partial_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 416 )
        
        # multi range request, not currently supported
        
        path = '/get_files/file?file_id={}'.format( 1 )
        
        partial_headers = dict( headers )
        partial_headers[ 'Range' ] = 'bytes=100-199,300-399'
        
        connection.request( 'GET', path, headers = partial_headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 416 )
        
        #
        
        path = '/get_files/thumbnail?file_id={}'.format( 1 )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( hashlib.sha256( data ).digest(), thumb_hash )
        
        #
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/get_files/file?hash={}'.format( hash_hex )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( hashlib.sha256( data ).digest(), hash )
        
        #
        
        path = '/get_files/thumbnail?hash={}'.format( hash_hex )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( hashlib.sha256( data ).digest(), thumb_hash )
        
        # file path
        
        path = '/get_files/file_path?hash={}'.format( hash_hex )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        d = json.loads( text )
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( d[ 'path' ], os.path.join( TG.test_controller.db_dir, 'client_files', f'f{hash_hex[:2]}', f'{hash_hex}.png' ) )
        self.assertEqual( d[ 'filetype' ], 'image/png' )
        self.assertEqual( d[ 'size' ], 100 )
        
        # thumbnail path
        
        path = '/get_files/thumbnail_path?hash={}'.format( hash_hex )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        d = json.loads( text )
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( d[ 'path' ], os.path.join( TG.test_controller.db_dir, 'client_files', f't{hash_hex[:2]}', f'{hash_hex}.thumbnail' ) )
        
        # with "sha256:"" on the front
        
        path = '/get_files/thumbnail?hash={}{}'.format( 'sha256:', hash_hex )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( hashlib.sha256( data ).digest(), thumb_hash )
        
        # now 404
        
        hash_404 = os.urandom( 32 )
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 123456, hash_404, size = size, mime = mime, width = width, height = height, duration_ms = duration_ms )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, times_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
        TG.test_controller.SetRead( 'media_result', media_result )
        TG.test_controller.SetRead( 'media_results_from_ids', ( media_result, ) )
        
        #
        
        path = '/get_files/file?hash={}'.format( hash_404.hex() )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 404 )
        
        # this no longer 404s, it should give the hydrus thumb
        
        path = '/get_files/thumbnail?hash={}'.format( hash_404.hex() )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        with open( HydrusStaticDir.GetStaticPath( 'hydrus.png' ), 'rb' ) as f:
            
            expected_data = f.read()
            
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( data, expected_data )
        
        #
        
        os.unlink( file_path )
        os.unlink( thumb_path )
        
        # local paths
        
        path = '/get_files/local_file_storage_locations'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        d = json.loads( text )
        
        self.assertEqual( response.status, 200 )
        
        locations = d[ 'locations' ]
        
        self.assertEqual( len( locations ), 1 )
        
        self.assertEqual( locations[0][ 'ideal_weight' ], 1 )
        self.assertEqual( locations[0][ 'max_num_bytes' ], None )
        self.assertEqual( locations[0][ 'path' ], os.path.join( TG.test_controller.db_dir, 'client_files' ) )
        self.assertEqual( set( locations[0][ 'prefixes' ] ), set( HydrusFilesPhysicalStorage.IteratePrefixes( 'f' ) ).union( HydrusFilesPhysicalStorage.IteratePrefixes( 't' ) ) )
        
    
    def _test_permission_failures( self, connection, set_up_permissions ):
        
        pass
        
        # failed permission tests
        
    
    def test_client_api( self ):
        
        host = '127.0.0.1'
        port = 45869
        
        connection = http.client.HTTPConnection( host, port, timeout = 10 )
        
        self._test_basics( connection )
        set_up_permissions = self._test_client_api_basics( connection )
        self._test_get_services( connection, set_up_permissions )
        self._test_get_service_svg( connection, set_up_permissions )
        self._test_manage_database( connection, set_up_permissions )
        self._test_options( connection, set_up_permissions )
        self._test_add_files_add_file( connection, set_up_permissions )
        self._test_add_files_other_actions( connection, set_up_permissions )
        self._test_add_files_migrate_files( connection, set_up_permissions )
        self._test_add_files_generate_hashes( connection, set_up_permissions )
        self._test_add_notes( connection, set_up_permissions )
        self._test_edit_ratings( connection, set_up_permissions )
        self._test_edit_times( connection, set_up_permissions )
        self._test_edit_file_viewing_statistics( connection, set_up_permissions )
        self._test_add_tags( connection, set_up_permissions )
        self._test_add_tags_search_tags( connection, set_up_permissions )
        self._test_add_tags_get_tag_siblings_and_parents( connection, set_up_permissions )
        self._test_add_favourite_tags( connection, set_up_permissions )
        self._test_add_urls( connection, set_up_permissions )
        self._test_associate_urls( connection, set_up_permissions )
        self._test_manage_services( connection, set_up_permissions )
        self._test_manage_duplicates( connection, set_up_permissions )
        self._test_manage_duplicate_potential_pairs( connection, set_up_permissions )
        self._test_manage_cookies( connection, set_up_permissions )
        self._test_manage_headers( connection, set_up_permissions )
        self._test_manage_pages_media_viewers( connection, set_up_permissions )
        self._test_manage_pages( connection, set_up_permissions )
        self._test_search_files( connection, set_up_permissions )
        
        if CBOR_AVAILABLE:
            
            self._test_cbor( connection, set_up_permissions )
            
        
        self._test_search_files_predicate_parsing( connection, set_up_permissions )
        self._test_file_hashes( connection, set_up_permissions )
        self._test_file_metadata( connection, set_up_permissions )
        self._test_get_files( connection, set_up_permissions )
        self._test_permission_failures( connection, set_up_permissions )
        self._test_cors_fails( connection )
        
        connection.close()
        
        #
        
        port = 45899
        
        connection = http.client.HTTPConnection( host, port, timeout = 10 )
        
        self._test_cors_succeeds( connection )
        
    
