from . import ClientCaches
from . import ClientConstants as CC
from . import ClientAPI
from . import ClientLocalServer
from . import ClientLocalServerResources
from . import ClientMedia
from . import ClientRatings
from . import ClientSearch
from . import ClientServices
from . import ClientTags
import collections
import hashlib
import http.client
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusTags
from . import HydrusText
import json
import os
import random
import shutil
import time
import unittest
import urllib
from twisted.internet import reactor
from . import HydrusData
from . import HydrusGlobals as HG

class TestClientAPI( unittest.TestCase ):
    
    @classmethod
    def setUpClass( cls ):
        
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
        
        with open( os.path.join( HC.STATIC_DIR, 'hydrus.ico' ), 'rb' ) as f:
            
            favicon = f.read()
            
        
        connection.request( 'GET', '/favicon.ico' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, favicon )
        
    
    def _test_client_api_basics( self, connection ):
        
        # /api_version
        
        connection.request( 'GET', '/api_version' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'version' ], HC.CLIENT_API_VERSION )
        
        # /request_new_permissions
        
        def format_request_new_permissions_query( name, basic_permissions ):
            
            return '/request_new_permissions?name={}&basic_permissions={}'.format( urllib.parse.quote( name ), urllib.parse.quote( json.dumps( basic_permissions ) ) )
            
        
        # fail
        
        ClientAPI.api_request_dialog_open = False
        
        connection.request( 'GET', format_request_new_permissions_query( 'test', [ ClientAPI.CLIENT_API_PERMISSION_ADD_FILES ] ) )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 403 )
        
        self.assertIn( 'dialog', text )
        
        # success
        
        permissions_to_set_up = []
        
        permissions_to_set_up.append( ( 'everything', list( ClientAPI.ALLOWED_PERMISSIONS ) ) )
        permissions_to_set_up.append( ( 'add_files', [ ClientAPI.CLIENT_API_PERMISSION_ADD_FILES ] ) )
        permissions_to_set_up.append( ( 'add_tags', [ ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS ] ) )
        permissions_to_set_up.append( ( 'add_urls', [ ClientAPI.CLIENT_API_PERMISSION_ADD_URLS ] ) )
        permissions_to_set_up.append( ( 'manage_pages', [ ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES ] ) )
        permissions_to_set_up.append( ( 'search_all_files', [ ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES ] ) )
        permissions_to_set_up.append( ( 'search_green_files', [ ClientAPI.CLIENT_API_PERMISSION_SEARCH_FILES ] ) )
        
        set_up_permissions = {}
        
        for ( name, basic_permissions ) in permissions_to_set_up:
            
            ClientAPI.api_request_dialog_open = True
            
            connection.request( 'GET', format_request_new_permissions_query( name, basic_permissions ) )
            
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
                
                search_tag_filter = ClientTags.TagFilter()
                
                search_tag_filter.SetRule( '', CC.FILTER_BLACKLIST )
                search_tag_filter.SetRule( ':', CC.FILTER_BLACKLIST )
                search_tag_filter.SetRule( 'green', CC.FILTER_WHITELIST )
                
                api_permissions.SetSearchTagFilter( search_tag_filter )
                
            
            self.assertEqual( bytes.fromhex( access_key_hex ), api_permissions.GetAccessKey() )
            
            set_up_permissions[ name ] = api_permissions
            
            HG.test_controller.client_api_manager.AddAccess( api_permissions )
            
        
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
                
                if request_type == 'header':
                    
                    headers = { key_name : key_hex }
                    
                    connection.request( 'GET', '/verify_access_key', headers = headers )
                    
                elif request_type == 'get':
                    
                    connection.request( 'GET', '/verify_access_key?{}={}'.format( key_name, key_hex ) )
                    
                
                response = connection.getresponse()
                
                data = response.read()
                
                text = str( data, 'utf-8' )
                
                self.assertEqual( response.status, 200 )
                
                body_dict = json.loads( text )
                
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
        
        headers = { 'Content-Type' : HC.mime_string_lookup[ HC.APPLICATION_JSON ] }
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'Hydrus-Client-API-Access-Key' : 'abcd', 'hash' : hash_hex, 'service_names_to_tags' : { 'local tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : 'abcd', 'hash' : hash_hex, 'service_names_to_tags' : { 'local tags' : [ 'test', 'test2' ] } }
        
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
        
        headers = { 'Content-Type' : HC.mime_string_lookup[ HC.APPLICATION_JSON ] }
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'hash' : hash_hex, 'service_names_to_tags' : { 'local tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : session_key_hex, 'hash' : hash_hex, 'service_names_to_tags' : { 'local tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
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
        self.assertEqual( response.getheader( 'Access-Control-Allow-Headers' ), 'Hydrus-Client-API-Access-Key' )
        self.assertEqual( response.getheader( 'Access-Control-Allow-Origin' ), '*' )
        
    
    def _test_add_files( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'add_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        # fail
        
        HG.test_controller.SetRead( 'hash_status', ( CC.STATUS_UNKNOWN, None, '' ) )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_string_lookup[ HC.APPLICATION_OCTET_STREAM ] }
        
        path = '/add_files/add_file'
        
        body = b'blarg'
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'status' ], CC.STATUS_ERROR )
        self.assertEqual( response_json[ 'hash' ], 'a593942cb7ea9ffcd8ccf2f0fa23c338e23bfecd9a3e508dfc0bcf07501ead08' )
        self.assertIn( 'Traceback', response_json[ 'note' ] )
        
        # success as body
        
        hydrus_png_path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        with open( hydrus_png_path, 'rb' ) as f:
            
            HYDRUS_PNG_BYTES = f.read()
            
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_string_lookup[ HC.APPLICATION_OCTET_STREAM ] }
        
        path = '/add_files/add_file'
        
        body = HYDRUS_PNG_BYTES
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        expected_result = { 'status' : CC.STATUS_SUCCESSFUL_AND_NEW, 'hash' : 'ad6d3599a6c489a575eb19c026face97a9cd6579e74728b0ce94a601d232f3c3' , 'note' : 'test note' }
        
        self.assertEqual( response_json, expected_result )
        
        # do hydrus png as path
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/add_files/add_file'
        
        body_dict = { 'path' : hydrus_png_path }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        expected_result = { 'status' : CC.STATUS_SUCCESSFUL_AND_NEW, 'hash' : 'ad6d3599a6c489a575eb19c026face97a9cd6579e74728b0ce94a601d232f3c3' , 'note' : 'test note' }
        
        self.assertEqual( response_json, expected_result )
        
    
    def _test_add_tags( self, connection, set_up_permissions ):
        
        # get services
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        path = '/add_tags/get_tag_services'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_answer = {}
        
        expected_answer[ 'local_tags' ] = [ "local tags" ]
        expected_answer[ 'tag_repositories' ] = [ "example tag repo" ]
        
        self.assertEqual( d, expected_answer )
        
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
        
        expected_answer = {}
        
        clean_tags = [ "bikini", "blue eyes", "character:samus aran", "::)", "10", "11", "9", "wew", "flower" ]
        
        clean_tags = HydrusTags.SortNumericTags( clean_tags )
        
        expected_answer[ 'tags' ] = clean_tags
        
        self.assertEqual( d, expected_answer )
        
        # add tags
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_string_lookup[ HC.APPLICATION_JSON ] }
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        hash2 = os.urandom( 32 )
        hash2_hex = hash2.hex()
        
        # missing hashes
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'service_names_to_tags' : { 'local tags' : [ 'test' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 )
        
        # invalid service key
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_names_to_tags' : { 'bad tag service' : [ 'test' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 )
        
        # add tags to local
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_names_to_tags' : { 'local tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test', set( [ hash ] ) ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test2', set( [ hash ] ) ) ) ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( len( service_keys_to_content_updates ), len( expected_service_keys_to_content_updates ) )
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            expected_content_updates = expected_service_keys_to_content_updates[ service_key ]
            
            c_u_tuples = [ c_u.ToTuple() for c_u in content_updates ]
            e_c_u_tuples = [ e_c_u.ToTuple() for e_c_u in expected_content_updates ]
            
            c_u_tuples.sort()
            e_c_u_tuples.sort()
            
            self.assertEqual( c_u_tuples, e_c_u_tuples )
            
        
        # add to multiple files
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hashes' : [ hash_hex, hash2_hex ], 'service_names_to_tags' : { 'local tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test', set( [ hash, hash2 ] ) ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test2', set( [ hash, hash2 ] ) ) ) ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( len( service_keys_to_content_updates ), len( expected_service_keys_to_content_updates ) )
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            expected_content_updates = expected_service_keys_to_content_updates[ service_key ]
            
            c_u_tuples = [ c_u.ToTuple() for c_u in content_updates ]
            e_c_u_tuples = [ e_c_u.ToTuple() for e_c_u in expected_content_updates ]
            
            c_u_tuples.sort()
            e_c_u_tuples.sort()
            
            self.assertEqual( c_u_tuples, e_c_u_tuples )
            
        
        # siblings and parents
        
        # setting up
        
        old_sib = HG.test_controller.tag_siblings_manager
        old_par = HG.test_controller.tag_parents_manager
        
        tag_siblings = collections.defaultdict( HydrusData.default_dict_set )
        
        first_dict = HydrusData.default_dict_set()
        
        first_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'test', 'muh test' ) }
        
        tag_siblings[ CC.LOCAL_TAG_SERVICE_KEY ] = first_dict
        
        HG.test_controller.SetRead( 'tag_siblings', tag_siblings )
        
        tag_parents = collections.defaultdict( HydrusData.default_dict_set )
        
        first_dict = HydrusData.default_dict_set()
        
        first_dict[ HC.CONTENT_STATUS_CURRENT ] = { ( 'muh test', 'muh test parent' ) }
        
        tag_parents[ CC.LOCAL_TAG_SERVICE_KEY ] = first_dict
        
        HG.test_controller.SetRead( 'tag_parents', tag_parents )
        
        HG.test_controller.tag_siblings_manager = ClientCaches.TagSiblingsManager( HG.test_controller )
        HG.test_controller.tag_parents_manager = ClientCaches.TagParentsManager( HG.test_controller )
        
        # ok, now with
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_names_to_tags' : { 'local tags' : [ 'test' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'muh test', set( [ hash ] ) ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'muh test parent', set( [ hash ] ) ) ) ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( len( service_keys_to_content_updates ), len( expected_service_keys_to_content_updates ) )
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            expected_content_updates = expected_service_keys_to_content_updates[ service_key ]
            
            c_u_tuples = [ c_u.ToTuple() for c_u in content_updates ]
            e_c_u_tuples = [ e_c_u.ToTuple() for e_c_u in expected_content_updates ]
            
            c_u_tuples.sort()
            e_c_u_tuples.sort()
            
            self.assertEqual( c_u_tuples, e_c_u_tuples )
            
        
        # and without
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_names_to_tags' : { 'local tags' : [ 'test' ] }, 'add_siblings_and_parents' : False }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test', set( [ hash ] ) ) ) ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( len( service_keys_to_content_updates ), len( expected_service_keys_to_content_updates ) )
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            expected_content_updates = expected_service_keys_to_content_updates[ service_key ]
            
            c_u_tuples = [ c_u.ToTuple() for c_u in content_updates ]
            e_c_u_tuples = [ e_c_u.ToTuple() for e_c_u in expected_content_updates ]
            
            c_u_tuples.sort()
            e_c_u_tuples.sort()
            
            self.assertEqual( c_u_tuples, e_c_u_tuples )
            
        
        # cleanup
        
        HG.test_controller.tag_siblings_manager = old_sib
        HG.test_controller.tag_parents_manager = old_par
        
    
    def _test_add_urls( self, connection, set_up_permissions ):
        
        # get url files
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        # none
        
        url = 'https://muhsite.wew/help_compute'
        
        HG.test_controller.SetRead( 'url_statuses', [] )
        
        path = '/add_urls/get_url_files?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_answer = {}
        
        expected_answer[ 'normalised_url' ] = url
        expected_answer[ 'url_file_statuses' ] = []
        
        self.assertEqual( d, expected_answer )
        
        # some
        
        url = 'http://safebooru.org/index.php?page=post&s=view&id=2753608'
        normalised_url = 'https://safebooru.org/index.php?id=2753608&page=post&s=view'
        
        hash = os.urandom( 32 )
        
        url_file_statuses = [ ( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, hash, 'muh import phrase' ) ]
        json_url_file_statuses = [ { 'status' : CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, 'hash' : hash.hex(), 'note' : 'muh import phrase' } ]
        
        HG.test_controller.SetRead( 'url_statuses', url_file_statuses )
        
        path = '/add_urls/get_url_files?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_answer = {}
        
        expected_answer[ 'normalised_url' ] = normalised_url
        expected_answer[ 'url_file_statuses' ] = json_url_file_statuses
        
        self.assertEqual( d, expected_answer )
        
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
        
        expected_answer = {}
        
        expected_answer[ 'normalised_url' ] = url
        expected_answer[ 'url_type' ] = HC.URL_TYPE_UNKNOWN
        expected_answer[ 'url_type_string' ] = 'unknown url'
        expected_answer[ 'match_name' ] = 'unknown url'
        expected_answer[ 'can_parse' ] = False
        
        self.assertEqual( d, expected_answer )
        
        # known
        
        url = 'http://8ch.net/tv/res/1846574.html'
        normalised_url = 'https://8ch.net/tv/res/1846574.html'
        # http so we can test normalised is https
        
        path = '/add_urls/get_url_info?url={}'.format( urllib.parse.quote( url, safe = '' ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_answer = {}
        
        expected_answer = { 'url_type' : HC.URL_TYPE_WATCHABLE, 'url_type_string' : 'watchable url', 'match_name' : '8chan thread', 'can_parse' : True }
        
        expected_answer[ 'normalised_url' ] = normalised_url
        expected_answer[ 'url_type' ] = HC.URL_TYPE_WATCHABLE
        expected_answer[ 'url_type_string' ] = 'watchable url'
        expected_answer[ 'match_name' ] = '8chan thread'
        expected_answer[ 'can_parse' ] = True
        
        self.assertEqual( d, expected_answer )
        
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
        
        expected_answer = {}
        
        expected_answer[ 'normalised_url' ] = normalised_url
        expected_answer[ 'url_type' ] = HC.URL_TYPE_POST
        expected_answer[ 'url_type_string' ] = 'post url'
        expected_answer[ 'match_name' ] = 'safebooru file page'
        expected_answer[ 'can_parse' ] = True
        
        self.assertEqual( d, expected_answer )
        
        # add url
        
        HG.test_controller.ClearWrites( 'import_url_test' )
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_string_lookup[ HC.APPLICATION_JSON ] }
        
        url = 'http://8ch.net/tv/res/1846574.html'
        
        request_dict = { 'url' : url }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://8ch.net/tv/res/1846574.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://8ch.net/tv/res/1846574.html' )
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, None, None, None, False ), {} ) ] )
        
        # with name
        
        HG.test_controller.ClearWrites( 'import_url_test' )
        
        request_dict = { 'url' : url, 'destination_page_name' : 'muh /tv/' }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://8ch.net/tv/res/1846574.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://8ch.net/tv/res/1846574.html' )
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, None, 'muh /tv/', None, False ), {} ) ] )
        
        # with page_key
        
        HG.test_controller.ClearWrites( 'import_url_test' )
        
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
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://8ch.net/tv/res/1846574.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://8ch.net/tv/res/1846574.html' )
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, None, None, page_key, False ), {} ) ] )
        
        # add tags and name, and show destination page
        
        HG.test_controller.ClearWrites( 'import_url_test' )
        
        request_dict = { 'url' : url, 'destination_page_name' : 'muh /tv/', 'show_destination_page' : True, 'service_names_to_tags' : { 'local tags' : [ '/tv/ thread' ] } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://8ch.net/tv/res/1846574.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://8ch.net/tv/res/1846574.html' )
        
        service_keys_to_tags = ClientTags.ServiceKeysToTags( { CC.LOCAL_TAG_SERVICE_KEY : set( [ '/tv/ thread' ] ) } )
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, service_keys_to_tags, 'muh /tv/', None, True ), {} ) ] )
        
        # associate url
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        url = 'https://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'url_to_add' : url, 'hash' : hash.hex() }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( [ url ], [ hash ] ) ) ]
        
        expected_result = [ ( ( expected_service_keys_to_content_updates, ), {} ) ]
        
        result = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( result, expected_result )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        url = 'https://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'urls_to_add' : [ url ], 'hashes' : [ hash.hex() ] }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_ADD, ( [ url ], [ hash ] ) ) ]
        
        expected_result = [ ( ( expected_service_keys_to_content_updates, ), {} ) ]
        
        result = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( result, expected_result )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        url = 'http://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'url_to_delete' : url, 'hash' : hash.hex() }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( [ url ], [ hash ] ) ) ]
        
        expected_result = [ ( ( expected_service_keys_to_content_updates, ), {} ) ]
        
        result = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( result, expected_result )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        hash = bytes.fromhex( '3b820114f658d768550e4e3d4f1dced3ff8db77443472b5ad93700647ad2d3ba' )
        url = 'http://rule34.xxx/index.php?id=2588418&page=post&s=view'
        
        request_dict = { 'urls_to_delete' : [ url ], 'hashes' : [ hash.hex() ] }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/associate_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.COMBINED_LOCAL_FILE_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_URLS, HC.CONTENT_UPDATE_DELETE, ( [ url ], [ hash ] ) ) ]
        
        expected_result = [ ( ( expected_service_keys_to_content_updates, ), {} ) ]
        
        result = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertEqual( result, expected_result )
        
    
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
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_string_lookup[ HC.APPLICATION_JSON ] }
        
        path = '/manage_pages/focus_page'
        
        page_key = os.urandom( 32 )
        
        request_dict = { 'page_key' : page_key.hex() }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        result = HG.test_controller.GetWrite( 'show_page' )
        
        expected_result = [ ( ( page_key, ), {} ) ]
        
        self.assertEqual( result, expected_result )
        
    
    def _test_search_files( self, connection, set_up_permissions ):
        
        hash_ids = [ 1, 2, 3, 4, 5, 10 ]
        
        HG.test_controller.SetRead( 'file_query_ids', set( hash_ids ) )
        
        # search files failed tag permission
        
        api_permissions = set_up_permissions[ 'search_green_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        tags = []
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        #
        
        tags = [ 'kino' ]
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # search files
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_answer = { 'file_ids' : hash_ids }
        
        self.assertEqual( d, expected_answer )
        
        # some file search param parsing
        
        class PretendRequest( object ):
            
            pass
            
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = {}
        pretend_request.client_api_permissions = set_up_permissions[ 'everything' ]
        
        predicates = ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
        
        self.assertEqual( predicates, [] )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'system_inbox' : True }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
            
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ '-green' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
            
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green', '-kino' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_TAG, value = 'kino', inclusive = False ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green' ], 'system_inbox' : True }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_SYSTEM_INBOX ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green' ], 'system_archive' : True }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearch.Predicate( predicate_type = HC.PREDICATE_TYPE_SYSTEM_ARCHIVE ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        # test file metadata
        
        api_permissions = set_up_permissions[ 'search_green_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        file_ids_to_hashes = { 1 : bytes.fromhex( 'a' * 64 ), 2 : bytes.fromhex( 'b' * 64 ), 3 : bytes.fromhex( 'c' * 64 ) }
        
        metadata = []
        
        for ( file_id, hash ) in file_ids_to_hashes.items():
            
            metadata_row = { 'file_id' : file_id, 'hash' : hash.hex() }
            
            metadata.append( metadata_row )
            
        
        expected_identifier_result = { 'metadata' : metadata }
        
        media_results = []
        
        for ( file_id, hash ) in file_ids_to_hashes.items():
            
            size = random.randint( 8192, 20 * 1048576 )
            mime = random.choice( [ HC.IMAGE_JPEG, HC.VIDEO_WEBM, HC.APPLICATION_PDF ] )
            width = random.randint( 200, 4096 )
            height = random.randint( 200, 4096 )
            duration = random.choice( [ 220, 16.66667, None ] )
            
            file_info_manager = ClientMedia.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration = duration )
            
            service_keys_to_statuses_to_tags = { CC.LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue eyes', 'blonde hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit' ] } }
            
            tags_manager = ClientMedia.TagsManager( service_keys_to_statuses_to_tags )
            
            locations_manager = ClientMedia.LocationsManager( set(), set(), set(), set() )
            ratings_manager = ClientRatings.RatingsManager( {} )
            file_viewing_stats_manager = ClientMedia.FileViewingStatsManager( 0, 0, 0, 0 )
            
            media_result = ClientMedia.MediaResult( file_info_manager, tags_manager, locations_manager, ratings_manager, file_viewing_stats_manager )
            
            media_results.append( media_result )
            
        
        metadata = []
        
        services_manager = HG.client_controller.services_manager
        
        service_keys_to_names = {}
        
        for media_result in media_results:
            
            metadata_row = {}
            
            file_info_manager = media_result.GetFileInfoManager()
            
            metadata_row[ 'file_id' ] = file_info_manager.hash_id
            metadata_row[ 'hash' ] = file_info_manager.hash.hex()
            metadata_row[ 'size' ] = file_info_manager.size
            metadata_row[ 'mime' ] = HC.mime_string_lookup[ file_info_manager.mime ]
            metadata_row[ 'width' ] = file_info_manager.width
            metadata_row[ 'height' ] = file_info_manager.height
            metadata_row[ 'duration' ] = file_info_manager.duration
            metadata_row[ 'num_frames' ] = file_info_manager.num_frames
            metadata_row[ 'num_words' ] = file_info_manager.num_words
            
            tags_manager = media_result.GetTagsManager()
            
            service_names_to_statuses_to_tags = {}
            
            service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags()
            
            for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                
                if service_key not in service_keys_to_names:
                    
                    service_keys_to_names[ service_key ] = services_manager.GetName( service_key )
                    
                
                service_name = service_keys_to_names[ service_key ]
                
                service_names_to_statuses_to_tags[ service_name ] = { str( status ) : list( tags ) for ( status, tags ) in statuses_to_tags.items() }
                
            
            metadata_row[ 'service_names_to_statuses_to_tags' ] = service_names_to_statuses_to_tags
            
            metadata.append( metadata_row )
            
        
        expected_metadata_result = { 'metadata' : metadata }
        
        HG.test_controller.SetRead( 'hash_ids_to_hashes', file_ids_to_hashes )
        HG.test_controller.SetRead( 'media_results', media_results )
        HG.test_controller.SetRead( 'media_results_from_ids', media_results )
        
        api_permissions.SetLastSearchResults( [ 1, 2, 3, 4, 5, 6 ] )
        
        # fail on non-permitted files
        
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
        
        path = '/get_files/file_metadata?file_ids={}&only_return_identifiers=true'.format( urllib.parse.quote( json.dumps( [ 1, 2, 3 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_identifier_result )
        
        # metadata from file_ids
        
        path = '/get_files/file_metadata?file_ids={}'.format( urllib.parse.quote( json.dumps( [ 1, 2, 3 ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_metadata_result )
        
        # now from hashes
        
        api_permissions = set_up_permissions[ 'everything' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        # identifiers from hashes
        
        path = '/get_files/file_metadata?hashes={}&only_return_identifiers=true'.format( urllib.parse.quote( json.dumps( [ hash.hex() for hash in file_ids_to_hashes.values() ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_identifier_result )
        
        # metadata from hashes
        
        path = '/get_files/file_metadata?hashes={}'.format( urllib.parse.quote( json.dumps( [ hash.hex() for hash in file_ids_to_hashes.values() ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_metadata_result )
        
        # files and thumbs
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        hash_hex = hash.hex()
        
        size = 100
        mime = HC.IMAGE_PNG
        width = 20
        height = 20
        duration = None
        
        file_info_manager = ClientMedia.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration = duration )
        
        service_keys_to_statuses_to_tags = { CC.LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue eyes', 'blonde hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit' ] } }
        
        tags_manager = ClientMedia.TagsManager( service_keys_to_statuses_to_tags )
        
        locations_manager = ClientMedia.LocationsManager( set(), set(), set(), set() )
        ratings_manager = ClientRatings.RatingsManager( {} )
        file_viewing_stats_manager = ClientMedia.FileViewingStatsManager( 0, 0, 0, 0 )
        
        media_result = ClientMedia.MediaResult( file_info_manager, tags_manager, locations_manager, ratings_manager, file_viewing_stats_manager )
        
        HG.test_controller.SetRead( 'media_results', ( media_result, ) )
        HG.test_controller.SetRead( 'media_results_from_ids', ( media_result, ) )
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        file_path = HG.test_controller.client_files_manager.GetFilePath( hash, HC.IMAGE_PNG, check_file_exists = False )
        
        shutil.copy2( path, file_path )
        
        thumb_hash = b'\x17\xde\xd6\xee\x1b\xfa\x002\xbdj\xc0w\x92\xce5\xf0\x12~\xfe\x915\xb3\xb3tA\xac\x90F\x95\xc2T\xc5'
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus_small.png' )
        
        thumb_path = HG.test_controller.client_files_manager._GenerateExpectedThumbnailPath( hash )
        
        shutil.copy2( path, thumb_path )
        
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
        
        # now 404
        
        hash_404 = os.urandom( 32 )
        
        file_info_manager = ClientMedia.FileInfoManager( 123456, hash_404, size = size, mime = mime, width = width, height = height, duration = duration )
        
        media_result = ClientMedia.MediaResult( file_info_manager, tags_manager, locations_manager, ratings_manager, file_viewing_stats_manager )
        
        HG.test_controller.SetRead( 'media_results', ( media_result, ) )
        HG.test_controller.SetRead( 'media_results_from_ids', ( media_result, ) )
        
        #
        
        path = '/get_files/file?hash={}'.format( hash_404.hex() )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 404 )
        
        #
        
        path = '/get_files/thumbnail?hash={}'.format( hash_404.hex() )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 404 )
        
        #
        
        os.unlink( file_path )
        os.unlink( thumb_path )
        
    
    def _test_permission_failures( self, connection, set_up_permissions ):
        
        pass
        
        # failed permission tests
        
    
    def test_client_api( self ):
        
        host = '127.0.0.1'
        port = 45869
        
        connection = http.client.HTTPConnection( host, port, timeout = 10 )
        
        self._test_basics( connection )
        set_up_permissions = self._test_client_api_basics( connection )
        self._test_add_files( connection, set_up_permissions )
        self._test_add_tags( connection, set_up_permissions )
        self._test_add_urls( connection, set_up_permissions )
        self._test_manage_pages( connection, set_up_permissions )
        self._test_search_files( connection, set_up_permissions )
        self._test_permission_failures( connection, set_up_permissions )
        self._test_cors_fails( connection )
        
        connection.close()
        
        #
        
        port = 45899
        
        connection = http.client.HTTPConnection( host, port, timeout = 10 )
        
        self._test_cors_succeeds( connection )
        
    
