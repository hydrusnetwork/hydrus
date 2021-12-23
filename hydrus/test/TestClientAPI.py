import collections
import hashlib
import http.client
import json
import os
import random
import shutil
import time
import unittest
import urllib

from twisted.internet import reactor

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTags
from hydrus.core import HydrusText

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientAPI
from hydrus.client import ClientManagers
from hydrus.client import ClientSearch
from hydrus.client import ClientServices
from hydrus.client.importing import ClientImportFiles
from hydrus.client.media import ClientMedia
from hydrus.client.media import ClientMediaManagers
from hydrus.client.media import ClientMediaResult
from hydrus.client.metadata import ClientTags
from hydrus.client.networking import ClientLocalServer
from hydrus.client.networking import ClientLocalServerResources
from hydrus.client.networking import ClientNetworkingContexts

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
        
    
    def _compare_content_updates( self, service_keys_to_content_updates, expected_service_keys_to_content_updates ):
        
        self.assertEqual( len( service_keys_to_content_updates ), len( expected_service_keys_to_content_updates ) )
        
        for ( service_key, content_updates ) in service_keys_to_content_updates.items():
            
            expected_content_updates = expected_service_keys_to_content_updates[ service_key ]
            
            c_u_tuples = sorted( ( ( c_u.ToTuple(), c_u.GetReason() ) for c_u in content_updates ) )
            e_c_u_tuples = sorted( ( ( e_c_u.ToTuple(), e_c_u.GetReason() ) for e_c_u in expected_content_updates ) )
            
            self.assertEqual( c_u_tuples, e_c_u_tuples )
            
        
    
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
        
        time.sleep( 3 )
        
    
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
        
        def format_request_new_permissions_query( name, basic_permissions ):
            
            return '/request_new_permissions?name={}&basic_permissions={}'.format( urllib.parse.quote( name ), urllib.parse.quote( json.dumps( basic_permissions ) ) )
            
        
        # fail as dialog not open
        
        ClientAPI.api_request_dialog_open = False
        
        connection.request( 'GET', format_request_new_permissions_query( 'test', [ ClientAPI.CLIENT_API_PERMISSION_ADD_FILES ] ) )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 409 )
        
        self.assertIn( 'dialog', text )
        
        # success
        
        permissions_to_set_up = []
        
        permissions_to_set_up.append( ( 'everything', list( ClientAPI.ALLOWED_PERMISSIONS ) ) )
        permissions_to_set_up.append( ( 'add_files', [ ClientAPI.CLIENT_API_PERMISSION_ADD_FILES ] ) )
        permissions_to_set_up.append( ( 'add_tags', [ ClientAPI.CLIENT_API_PERMISSION_ADD_TAGS ] ) )
        permissions_to_set_up.append( ( 'add_urls', [ ClientAPI.CLIENT_API_PERMISSION_ADD_URLS ] ) )
        permissions_to_set_up.append( ( 'manage_pages', [ ClientAPI.CLIENT_API_PERMISSION_MANAGE_PAGES ] ) )
        permissions_to_set_up.append( ( 'manage_cookies', [ ClientAPI.CLIENT_API_PERMISSION_MANAGE_COOKIES ] ) )
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
                
                search_tag_filter = HydrusTags.TagFilter()
                
                search_tag_filter.SetRule( '', HC.FILTER_BLACKLIST )
                search_tag_filter.SetRule( ':', HC.FILTER_BLACKLIST )
                search_tag_filter.SetRule( 'green', HC.FILTER_WHITELIST )
                
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
        
        headers = { 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'Hydrus-Client-API-Access-Key' : 'abcd', 'hash' : hash_hex, 'service_names_to_tags' : { 'my tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : 'abcd', 'hash' : hash_hex, 'service_names_to_tags' : { 'my tags' : [ 'test', 'test2' ] } }
        
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
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'hash' : hash_hex, 'service_names_to_tags' : { 'my tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : session_key_hex, 'hash' : hash_hex, 'service_names_to_tags' : { 'my tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertIn( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, service_keys_to_content_updates )
        self.assertTrue( len( service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] ) > 0 )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : session_key_hex, 'hash' : hash_hex, 'service_keys_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertIn( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, service_keys_to_content_updates )
        self.assertTrue( len( service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] ) > 0 )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        body_dict = { 'Hydrus-Client-API-Session-Key' : session_key_hex, 'hash' : hash_hex, 'service_keys_to_actions_to_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : { str( HC.CONTENT_UPDATE_ADD ) : [ 'test', 'test2' ] } } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self.assertIn( CC.DEFAULT_LOCAL_TAG_SERVICE_KEY, service_keys_to_content_updates )
        self.assertTrue( len( service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] ) > 0 )
        
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
        should_break = { set_up_permissions[ 'add_urls' ], set_up_permissions[ 'manage_cookies' ] }
        
        expected_answer = {
            'local_tags': [
                {
                    'name': 'my tags',
                    'service_key': '6c6f63616c2074616773'
                }
            ],
            'tag_repositories': [
                {
                    'name': 'example tag repo',
                    'service_key': HG.test_controller.example_tag_repo_service_key.hex()
                }
            ],
            'local_files': [
                {
                    'name': 'my files',
                    'service_key': '6c6f63616c2066696c6573'
                }
            ],
            'file_repositories': [
            ],
            'all_local_files': [
                { 
                    'name': 'all local files',
                    'service_key': '616c6c206c6f63616c2066696c6573'
                }
            ],
            'all_known_files': [
                {
                    'name': 'all known files',
                    'service_key': '616c6c206b6e6f776e2066696c6573'
                }
            ],
            'all_known_tags': [
                {
                    'name': 'all known tags',
                    'service_key': '616c6c206b6e6f776e2074616773'
                }
            ],
            'trash': [
                {
                    'name': 'trash',
                    'service_key': '7472617368'
                }
            ]
        }
        
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
                
                self.assertEqual( d, expected_answer )
                
            else:
                
                self.assertEqual( response.status, 403 )
                
            
        
    
    def _test_add_files_add_file( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'add_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        # fail
        
        hash = bytes.fromhex( 'a593942cb7ea9ffcd8ccf2f0fa23c338e23bfecd9a3e508dfc0bcf07501ead08' )
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        
        HG.test_controller.SetRead( 'hash_status', f )
        
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
        self.assertIn( 'Traceback', response_json[ 'note' ] )
        
        # success as body
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        f.note = 'test note'
        
        HG.test_controller.SetRead( 'hash_status', f )
        
        hydrus_png_path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
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
        
        self.assertEqual( response_json, expected_result )
        
        # do hydrus png as path
        
        f = ClientImportFiles.FileImportStatus.STATICGetUnknownStatus()
        
        f.hash = hash
        f.note = 'test note'
        
        HG.test_controller.SetRead( 'hash_status', f )
        
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
        
        self.assertEqual( response_json, expected_result )
        
    
    def _test_add_files_other_actions( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'add_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        #
        
        hash = HydrusData.GenerateKey()
        hashes = { HydrusData.GenerateKey() for i in range( 10 ) }
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/delete_files'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        expected_service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, { hash } ) ] }
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/delete_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ] }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        expected_service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_DELETE, hashes ) ] }
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/undelete_files'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        expected_service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, { hash } ) ] }
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/undelete_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ] }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        expected_service_keys_to_content_updates = { CC.LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_UNDELETE, hashes ) ] }
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/archive_files'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        expected_service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, { hash } ) ] }
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/archive_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ] }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        expected_service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_ARCHIVE, hashes ) ] }
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/unarchive_files'
        
        body_dict = { 'hash' : hash.hex() }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        expected_service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, { hash } ) ] }
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        #
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_files/unarchive_files'
        
        body_dict = { 'hashes' : [ h.hex() for h in hashes ] }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        expected_service_keys_to_content_updates = { CC.COMBINED_LOCAL_FILE_SERVICE_KEY : [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_FILES, HC.CONTENT_UPDATE_INBOX, hashes ) ] }
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
    
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
        
        expected_answer = {}
        
        clean_tags = [ "bikini", "blue eyes", "character:samus aran", "::)", "10", "11", "9", "wew", "flower" ]
        
        clean_tags = HydrusTags.SortNumericTags( clean_tags )
        
        expected_answer[ 'tags' ] = clean_tags
        
        self.assertEqual( d, expected_answer )
        
        # add tags
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
        hash = os.urandom( 32 )
        hash_hex = hash.hex()
        
        hash2 = os.urandom( 32 )
        hash2_hex = hash2.hex()
        
        # missing hashes
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'service_names_to_tags' : { 'my tags' : [ 'test' ] } }
        
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
        
        body_dict = { 'hash' : hash_hex, 'service_names_to_tags' : { 'my tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test', set( [ hash ] ) ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test2', set( [ hash ] ) ) ) ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        # add tags to local complex
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_names_to_actions_to_tags' : { 'my tags' : { str( HC.CONTENT_UPDATE_ADD ) : [ 'test_add', 'test_add2' ], str( HC.CONTENT_UPDATE_DELETE ) : [ 'test_delete', 'test_delete2' ] } } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [
            HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test_add', set( [ hash ] ) ) ),
            HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test_add2', set( [ hash ] ) ) ),
            HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test_delete', set( [ hash ] ) ) ),
            HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_DELETE, ( 'test_delete2', set( [ hash ] ) ) )
        ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        # pend tags to repo
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_names_to_tags' : { 'example tag repo' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ HG.test_controller.example_tag_repo_service_key ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'test', set( [ hash ] ) ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'test2', set( [ hash ] ) ) ) ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        # pend tags to repo complex
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hash' : hash_hex, 'service_names_to_actions_to_tags' : { 'example tag repo' : { str( HC.CONTENT_UPDATE_PEND ) : [ 'test_add', 'test_add2' ], str( HC.CONTENT_UPDATE_PETITION ) : [ [ 'test_delete', 'muh reason' ], 'test_delete2' ] } } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ HG.test_controller.example_tag_repo_service_key ] = [
            HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'test_add', set( [ hash ] ) ) ),
            HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PEND, ( 'test_add2', set( [ hash ] ) ) ),
            HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'test_delete', set( [ hash ] ) ), reason = 'muh reason' ),
            HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_PETITION, ( 'test_delete2', set( [ hash ] ) ), reason = 'Petitioned from API' )
        ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
        # add to multiple files
        
        HG.test_controller.ClearWrites( 'content_updates' )
        
        path = '/add_tags/add_tags'
        
        body_dict = { 'hashes' : [ hash_hex, hash2_hex ], 'service_names_to_tags' : { 'my tags' : [ 'test', 'test2' ] } }
        
        body = json.dumps( body_dict )
        
        connection.request( 'POST', path, body = body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        expected_service_keys_to_content_updates = collections.defaultdict( list )
        
        expected_service_keys_to_content_updates[ CC.DEFAULT_LOCAL_TAG_SERVICE_KEY ] = [ HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test', set( [ hash, hash2 ] ) ) ), HydrusData.ContentUpdate( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, ( 'test2', set( [ hash, hash2 ] ) ) ) ]
        
        [ ( ( service_keys_to_content_updates, ), kwargs ) ] = HG.test_controller.GetWrite( 'content_updates' )
        
        self._compare_content_updates( service_keys_to_content_updates, expected_service_keys_to_content_updates )
        
    
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
        
        url = 'http://safebooru.org/index.php?s=view&page=post&id=2753608'
        normalised_url = 'https://safebooru.org/index.php?id=2753608&page=post&s=view'
        
        hash = os.urandom( 32 )
        
        url_file_statuses = [ ClientImportFiles.FileImportStatus( CC.STATUS_SUCCESSFUL_BUT_REDUNDANT, hash, note = 'muh import phrase' ) ]
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
        expected_answer[ 'cannot_parse_reason' ] = 'unknown url class'
        
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
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex, 'Content-Type' : HC.mime_mimetype_string_lookup[ HC.APPLICATION_JSON ] }
        
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
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set(), ClientTags.ServiceKeysToTags(), None, None, False ), {} ) ] )
        
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
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set(), ClientTags.ServiceKeysToTags(), 'muh /tv/', None, False ), {} ) ] )
        
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
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set(), ClientTags.ServiceKeysToTags(), None, page_key, False ), {} ) ] )
        
        # add tags and name, and show destination page
        
        HG.test_controller.ClearWrites( 'import_url_test' )
        
        request_dict = { 'url' : url, 'destination_page_name' : 'muh /tv/', 'show_destination_page' : True, 'filterable_tags' : [ 'filename:yo' ], 'service_names_to_additional_tags' : { 'my tags' : [ '/tv/ thread' ] } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://8ch.net/tv/res/1846574.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://8ch.net/tv/res/1846574.html' )
        
        filterable_tags = [ 'filename:yo' ]
        additional_service_keys_to_tags = ClientTags.ServiceKeysToTags( { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : set( [ '/tv/ thread' ] ) } )
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set( filterable_tags ), additional_service_keys_to_tags, 'muh /tv/', None, True ), {} ) ] )
        
        # add tags with service key and name, and show destination page
        
        HG.test_controller.ClearWrites( 'import_url_test' )
        
        request_dict = { 'url' : url, 'destination_page_name' : 'muh /tv/', 'show_destination_page' : True, 'filterable_tags' : [ 'filename:yo' ], 'service_keys_to_additional_tags' : { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY.hex() : [ '/tv/ thread' ] } }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', '/add_urls/add_url', body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        response_json = json.loads( text )
        
        self.assertEqual( response_json[ 'human_result_text' ], '"https://8ch.net/tv/res/1846574.html" URL added successfully.' )
        self.assertEqual( response_json[ 'normalised_url' ], 'https://8ch.net/tv/res/1846574.html' )
        
        filterable_tags = [ 'filename:yo' ]
        additional_service_keys_to_tags = ClientTags.ServiceKeysToTags( { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : set( [ '/tv/ thread' ] ) } )
        
        self.assertEqual( HG.test_controller.GetWrite( 'import_url_test' ), [ ( ( url, set( filterable_tags ), additional_service_keys_to_tags, 'muh /tv/', None, True ), {} ) ] )
        
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
        
    
    def _test_manage_cookies( self, connection, set_up_permissions ):
        
        api_permissions = set_up_permissions[ 'manage_cookies' ]
        
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
        
        cookies.append( [ 'one', '1', '.somesite.com', '/', HydrusData.GetNow() + 86400 ] )
        cookies.append( [ 'two', '2', 'somesite.com', '/', HydrusData.GetNow() + 86400 ] )
        cookies.append( [ 'three', '3', 'wew.somesite.com', '/', HydrusData.GetNow() + 86400 ] )
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
        
        expected_cookies.append( [ 'two', '2', 'somesite.com', '/', HydrusData.GetNow() + 86400 ] )
        expected_cookies.append( [ 'three', '3', 'wew.somesite.com', '/', HydrusData.GetNow() + 86400 ] )
        expected_cookies.append( [ 'four', '4', '.somesite.com', '/', None ] )
        
        frozen_result_cookies = { tuple( row ) for row in result_cookies }
        frozen_expected_cookies = { tuple( row ) for row in expected_cookies }
        
        self.assertEqual( frozen_result_cookies, frozen_expected_cookies )
        
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
        
        current_headers = HG.test_controller.network_engine.domain_manager.GetHeaders( [ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ] )
        
        self.assertEqual( current_headers[ 'User-Agent' ], new_user_agent )
        
        #
        
        request_dict = { 'user-agent' : '' }
        
        request_body = json.dumps( request_dict )
        
        connection.request( 'POST', path, body = request_body, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        current_headers = HG.test_controller.network_engine.domain_manager.GetHeaders( [ ClientNetworkingContexts.GLOBAL_NETWORK_CONTEXT ] )
        
        from hydrus.client import ClientDefaults
        
        self.assertEqual( current_headers[ 'User-Agent' ], ClientDefaults.DEFAULT_USER_AGENT )
        
    
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
        
        HG.test_controller.SetRead( 'boned_stats', expected_data )
        
        path = '/manage_database/mr_bones'
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        boned_stats = d[ 'boned_stats' ]
        
        self.assertEqual( boned_stats, dict( expected_data ) )
        
    
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
        
        result = HG.test_controller.GetWrite( 'show_page' )
        
        expected_result = [ ( ( page_key, ), {} ) ]
        
        self.assertEqual( result, expected_result )
        
    
    def _test_search_files( self, connection, set_up_permissions ):
        
        hash_ids = [ 1, 2, 3, 4, 5, 10, 15, 16, 17, 18, 19, 20, 21, 25, 100, 101, 150 ]
        
        # search files failed tag permission
        
        api_permissions = set_up_permissions[ 'search_green_files' ]
        
        access_key_hex = api_permissions.GetAccessKey().hex()
        
        headers = { 'Hydrus-Client-API-Access-Key' : access_key_hex }
        
        #
        
        sample_hash_ids = set( random.sample( hash_ids, 3 ) )
        
        HG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = []
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        #
        
        sample_hash_ids = set( random.sample( hash_ids, 3 ) )
        
        HG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino' ]
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 403 )
        
        # search files
        
        HG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( hash_ids, 3 ) )
        
        HG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}'.format( urllib.parse.quote( json.dumps( tags ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        expected_answer = { 'file_ids' : list( sample_hash_ids ) }
        
        self.assertEqual( d, expected_answer )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetFileServiceKey(), CC.LOCAL_FILE_SERVICE_KEY )
        self.assertEqual( file_search_context.GetTagSearchContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_IMPORT_TIME ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_DESC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # sort
        
        # this just tests if it parses, we don't have a full test for read params yet
        
        HG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( hash_ids, 3 ) )
        
        HG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}'.format( urllib.parse.quote( json.dumps( tags ) ), CC.SORT_FILES_BY_FRAMERATE )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetFileServiceKey(), CC.LOCAL_FILE_SERVICE_KEY )
        self.assertEqual( file_search_context.GetTagSearchContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_FRAMERATE ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_DESC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # sort
        
        HG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( hash_ids, 3 ) )
        
        HG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}&file_sort_asc={}'.format( urllib.parse.quote( json.dumps( tags ) ), CC.SORT_FILES_BY_FRAMERATE, 'true' )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetFileServiceKey(), CC.LOCAL_FILE_SERVICE_KEY )
        self.assertEqual( file_search_context.GetTagSearchContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_FRAMERATE ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_ASC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # file domain
        
        HG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( hash_ids, 3 ) )
        
        HG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}&file_sort_asc={}&file_service_name={}'.format(
            urllib.parse.quote( json.dumps( tags ) ),
            CC.SORT_FILES_BY_FRAMERATE,
            'true',
            'trash'
        )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetFileServiceKey(), CC.TRASH_SERVICE_KEY )
        self.assertEqual( file_search_context.GetTagSearchContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_FRAMERATE ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_ASC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # file and tag domain
        
        HG.test_controller.ClearReads( 'file_query_ids' )
        
        sample_hash_ids = set( random.sample( hash_ids, 3 ) )
        
        HG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
        tags = [ 'kino', 'green' ]
        
        path = '/get_files/search_files?tags={}&file_sort_type={}&file_sort_asc={}&file_service_key={}&tag_service_name={}'.format(
            urllib.parse.quote( json.dumps( tags ) ),
            CC.SORT_FILES_BY_FRAMERATE,
            'true',
            CC.TRASH_SERVICE_KEY.hex(),
            'all%20known%20tags'
        )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetRead( 'file_query_ids' )
        
        ( file_search_context, ) = args
        
        self.assertEqual( file_search_context.GetFileServiceKey(), CC.TRASH_SERVICE_KEY )
        self.assertEqual( file_search_context.GetTagSearchContext().service_key, CC.COMBINED_TAG_SERVICE_KEY )
        self.assertEqual( set( file_search_context.GetPredicates() ), { ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_TAG, tag ) for tag in tags } )
        
        self.assertIn( 'sort_by', kwargs )
        
        sort_by = kwargs[ 'sort_by' ]
        
        self.assertEqual( sort_by.sort_type, ( 'system', CC.SORT_FILES_BY_FRAMERATE ) )
        self.assertEqual( sort_by.sort_order, CC.SORT_ASC )
        
        self.assertIn( 'apply_implicit_limit', kwargs )
        
        self.assertEqual( kwargs[ 'apply_implicit_limit' ], False )
        
        # file and tag domain
        
        # this just tests if it parses, we don't have a full test for read params yet
        
        sample_hash_ids = set( random.sample( hash_ids, 3 ) )
        
        HG.test_controller.SetRead( 'file_query_ids', set( sample_hash_ids ) )
        
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
        
    
    def _test_search_files_predicate_parsing( self, connection, set_up_permissions ):
        
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
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_TAG, value = 'kino', inclusive = False ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green' ], 'system_inbox' : True }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_INBOX ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green' ], 'system_archive' : True }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green', 'system:archive' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_TAG, value = 'green' ) )
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE ) )
        
        self.assertEqual( set( predicates ), set( expected_predicates ) )
        
        #
        
        pretend_request = PretendRequest()
        
        pretend_request.parsed_request_args = { 'tags' : [ 'green', [ 'red', 'blue' ], 'system:archive' ] }
        pretend_request.client_api_permissions = set_up_permissions[ 'search_green_files' ]
        
        predicates = ClientLocalServerResources.ParseClientAPISearchPredicates( pretend_request )
        
        expected_predicates = []
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_TAG, value = 'green' ) )
        
        expected_predicates.append(
            ClientSearch.Predicate(
                predicate_type = ClientSearch.PREDICATE_TYPE_OR_CONTAINER,
                value = [
                    ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_TAG, value = 'red' ),
                    ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_TAG, value = 'blue' )
                ]
            )
        )
        
        expected_predicates.append( ClientSearch.Predicate( predicate_type = ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVE ) )
        
        self.assertEqual( { pred for pred in predicates if pred.GetType() != ClientSearch.PREDICATE_TYPE_OR_CONTAINER }, { pred for pred in expected_predicates if pred.GetType() != ClientSearch.PREDICATE_TYPE_OR_CONTAINER } )
        self.assertEqual( { frozenset( pred.GetValue() ) for pred in predicates if pred.GetType() == ClientSearch.PREDICATE_TYPE_OR_CONTAINER }, { frozenset( pred.GetValue() ) for pred in expected_predicates if pred.GetType() == ClientSearch.PREDICATE_TYPE_OR_CONTAINER } )
        
    
    def _test_file_metadata( self, connection, set_up_permissions ):
        
        # test file metadata
        
        for hide_service_names_tags in ( False, True ):
            
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
            
            urls = { "https://gelbooru.com/index.php?page=post&s=view&id=4841557", "https://img2.gelbooru.com//images/80/c8/80c8646b4a49395fb36c805f316c49a9.jpg" }
            
            sorted_urls = sorted( urls )
            
            for ( file_id, hash ) in file_ids_to_hashes.items():
                
                size = random.randint( 8192, 20 * 1048576 )
                mime = random.choice( [ HC.IMAGE_JPEG, HC.VIDEO_WEBM, HC.APPLICATION_PDF ] )
                width = random.randint( 200, 4096 )
                height = random.randint( 200, 4096 )
                duration = random.choice( [ 220, 16.66667, None ] )
                has_audio = random.choice( [ True, False ] )
                
                file_info_manager = ClientMediaManagers.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration = duration, has_audio = has_audio )
                
                service_keys_to_statuses_to_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue_eyes', 'blonde_hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit' ] } }
                service_keys_to_statuses_to_display_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue eyes', 'blonde hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit', 'clothing' ] } }
                
                tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
                
                locations_manager = ClientMediaManagers.LocationsManager( dict(), dict(), set(), set(), inbox = False, urls = urls )
                ratings_manager = ClientMediaManagers.RatingsManager( {} )
                notes_manager = ClientMediaManagers.NotesManager( {} )
                file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager( 0, 0, 0, 0 )
                
                media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
                
                media_results.append( media_result )
                
            
            hide_service_names_tags_metadata = []
            metadata = []
            detailed_known_urls_metadata = []
            
            services_manager = HG.client_controller.services_manager
            
            service_keys_to_names = {}
            
            for media_result in media_results:
                
                metadata_row = {}
                
                file_info_manager = media_result.GetFileInfoManager()
                
                metadata_row[ 'file_id' ] = file_info_manager.hash_id
                metadata_row[ 'hash' ] = file_info_manager.hash.hex()
                metadata_row[ 'size' ] = file_info_manager.size
                metadata_row[ 'mime' ] = HC.mime_mimetype_string_lookup[ file_info_manager.mime ]
                metadata_row[ 'ext' ] = HC.mime_ext_lookup[ file_info_manager.mime ]
                metadata_row[ 'width' ] = file_info_manager.width
                metadata_row[ 'height' ] = file_info_manager.height
                metadata_row[ 'duration' ] = file_info_manager.duration
                metadata_row[ 'has_audio' ] = file_info_manager.has_audio
                metadata_row[ 'num_frames' ] = file_info_manager.num_frames
                metadata_row[ 'num_words' ] = file_info_manager.num_words
                
                metadata_row[ 'is_inbox' ] = False
                metadata_row[ 'is_local' ] = False
                metadata_row[ 'is_trashed' ] = False
                
                metadata_row[ 'known_urls' ] = list( sorted_urls )
                
                tags_manager = media_result.GetTagsManager()
                
                service_names_to_statuses_to_tags = {}
                api_service_keys_to_statuses_to_tags = {}
                
                service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_STORAGE )
                
                for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                    
                    if service_key not in service_keys_to_names:
                        
                        service_keys_to_names[ service_key ] = services_manager.GetName( service_key )
                        
                    
                    s = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                    
                    if len( s ) > 0:
                        
                        service_name = service_keys_to_names[ service_key ]
                        
                        service_names_to_statuses_to_tags[ service_name ] = s
                        api_service_keys_to_statuses_to_tags[ service_key.hex() ] = s
                        
                    
                
                metadata_row[ 'service_keys_to_statuses_to_tags' ] = api_service_keys_to_statuses_to_tags
                
                service_names_to_statuses_to_display_tags = {}
                service_keys_to_statuses_to_display_tags = {}
                
                service_keys_to_statuses_to_tags = tags_manager.GetServiceKeysToStatusesToTags( ClientTags.TAG_DISPLAY_ACTUAL )
                
                for ( service_key, statuses_to_tags ) in service_keys_to_statuses_to_tags.items():
                    
                    if service_key not in service_keys_to_names:
                        
                        service_keys_to_names[ service_key ] = services_manager.GetName( service_key )
                        
                    
                    s = { str( status ) : sorted( tags, key = HydrusTags.ConvertTagToSortable ) for ( status, tags ) in statuses_to_tags.items() if len( tags ) > 0 }
                    
                    if len( s ) > 0:
                        
                        service_name = service_keys_to_names[ service_key ]
                        
                        service_names_to_statuses_to_display_tags[ service_name ] = s
                        service_keys_to_statuses_to_display_tags[ service_key.hex() ] = s
                        
                    
                
                metadata_row[ 'service_keys_to_statuses_to_display_tags' ] = service_keys_to_statuses_to_display_tags
                
                hide_service_names_tags_metadata.append( metadata_row )
                
                metadata_row = dict( metadata_row )
                
                metadata_row[ 'service_names_to_statuses_to_tags' ] = service_names_to_statuses_to_tags
                metadata_row[ 'service_names_to_statuses_to_display_tags' ] = service_names_to_statuses_to_display_tags
                
                metadata.append( metadata_row )
                
                detailed_known_urls_metadata_row = dict( metadata_row )
                
                detailed_known_urls_metadata_row[ 'detailed_known_urls' ] = [
                    {'normalised_url': 'https://gelbooru.com/index.php?id=4841557&page=post&s=view', 'url_type': 0, 'url_type_string': 'post url', 'match_name': 'gelbooru file page', 'can_parse': True},
                    {'normalised_url': 'https://img2.gelbooru.com//images/80/c8/80c8646b4a49395fb36c805f316c49a9.jpg', 'url_type': 5, 'url_type_string': 'unknown url', 'match_name': 'unknown url', 'can_parse': False, 'cannot_parse_reason' : 'unknown url class'}
                ]
                
                detailed_known_urls_metadata.append( detailed_known_urls_metadata_row )
                
            
            expected_hide_service_names_tags_metadata_result = { 'metadata' : hide_service_names_tags_metadata }
            expected_metadata_result = { 'metadata' : metadata }
            expected_detailed_known_urls_metadata_result = { 'metadata' : detailed_known_urls_metadata }
            
        
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
        
        # fails on borked hashes
        
        path = '/get_files/file_metadata?hashes={}'.format( urllib.parse.quote( json.dumps( [ 'deadbeef' ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 400 )
        
        # hide service names to tags
        
        path = '/get_files/file_metadata?hashes={}&hide_service_names_tags=true'.format( urllib.parse.quote( json.dumps( [ hash.hex() for hash in file_ids_to_hashes.values() ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_hide_service_names_tags_metadata_result )
        
        # metadata from hashes with detailed url info
        
        path = '/get_files/file_metadata?hashes={}&detailed_url_information=true'.format( urllib.parse.quote( json.dumps( [ hash.hex() for hash in file_ids_to_hashes.values() ] ) ) )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        text = str( data, 'utf-8' )
        
        self.assertEqual( response.status, 200 )
        
        d = json.loads( text )
        
        self.assertEqual( d, expected_detailed_known_urls_metadata_result )
        
        # failure on missing file_ids
        
        HG.test_controller.SetRead( 'media_results_from_ids', HydrusExceptions.DataMissing( 'test missing' ) )
        
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
        
    
    def _test_get_files( self, connection, set_up_permissions ):
        
        # files and thumbs
        
        file_id = 1
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        hash_hex = hash.hex()
        
        size = 100
        mime = HC.IMAGE_PNG
        width = 20
        height = 20
        duration = None
        
        file_info_manager = ClientMediaManagers.FileInfoManager( file_id, hash, size = size, mime = mime, width = width, height = height, duration = duration )
        
        service_keys_to_statuses_to_tags = { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue_eyes', 'blonde_hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit' ] } }
        service_keys_to_statuses_to_display_tags =  { CC.DEFAULT_LOCAL_TAG_SERVICE_KEY : { HC.CONTENT_STATUS_CURRENT : [ 'blue eyes', 'blonde hair' ], HC.CONTENT_STATUS_PENDING : [ 'bodysuit', 'clothing' ] } }
        
        tags_manager = ClientMediaManagers.TagsManager( service_keys_to_statuses_to_tags, service_keys_to_statuses_to_display_tags )
        
        locations_manager = ClientMediaManagers.LocationsManager( dict(), dict(), set(), set() )
        ratings_manager = ClientMediaManagers.RatingsManager( {} )
        notes_manager = ClientMediaManagers.NotesManager( {} )
        file_viewing_stats_manager = ClientMediaManagers.FileViewingStatsManager( 0, 0, 0, 0 )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
        HG.test_controller.SetRead( 'media_result', media_result )
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
        
        # with "sha256:"" on the front
        
        path = '/get_files/thumbnail?hash={}{}'.format( 'sha256:', hash_hex )
        
        connection.request( 'GET', path, headers = headers )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( response.status, 200 )
        
        self.assertEqual( hashlib.sha256( data ).digest(), thumb_hash )
        
        # now 404
        
        hash_404 = os.urandom( 32 )
        
        file_info_manager = ClientMediaManagers.FileInfoManager( 123456, hash_404, size = size, mime = mime, width = width, height = height, duration = duration )
        
        media_result = ClientMediaResult.MediaResult( file_info_manager, tags_manager, locations_manager, ratings_manager, notes_manager, file_viewing_stats_manager )
        
        HG.test_controller.SetRead( 'media_result', media_result )
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
        self._test_get_services( connection, set_up_permissions )
        self._test_manage_database( connection, set_up_permissions )
        self._test_add_files_add_file( connection, set_up_permissions )
        self._test_add_files_other_actions( connection, set_up_permissions )
        self._test_add_tags( connection, set_up_permissions )
        self._test_add_urls( connection, set_up_permissions )
        self._test_manage_cookies( connection, set_up_permissions )
        self._test_manage_pages( connection, set_up_permissions )
        self._test_search_files( connection, set_up_permissions )
        self._test_search_files_predicate_parsing( connection, set_up_permissions )
        self._test_file_metadata( connection, set_up_permissions )
        self._test_get_files( connection, set_up_permissions )
        self._test_permission_failures( connection, set_up_permissions )
        self._test_cors_fails( connection )
        
        connection.close()
        
        #
        
        port = 45899
        
        connection = http.client.HTTPConnection( host, port, timeout = 10 )
        
        self._test_cors_succeeds( connection )
        
    
