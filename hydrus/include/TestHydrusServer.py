from . import ClientConstants as CC
from . import ClientAPI
from . import ClientLocalServer
from . import ClientMedia
from . import ClientRatings
from . import ClientServices
from . import ClientTags
import hashlib
import http.client
from . import HydrusConstants as HC
from . import HydrusEncryption
from . import HydrusNetwork
from . import HydrusPaths
from . import HydrusServer
from . import HydrusServerResources
from . import HydrusText
import json
import os
import random
from . import ServerFiles
from . import ServerServer
import ssl
from . import TestController
import time
import unittest
import urllib
from twisted.internet import reactor
#from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.defer import deferredGenerator, waitForDeferred
import twisted.internet.ssl
from . import HydrusData
from . import HydrusGlobals as HG

with open( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), 'rb' ) as f:
    
    EXAMPLE_FILE = f.read()
    
with open( os.path.join( HC.STATIC_DIR, 'hydrus_small.png' ), 'rb' ) as f:
    
    EXAMPLE_THUMBNAIL = f.read()
    
class TestServer( unittest.TestCase ):
    
    @classmethod
    def setUpClass( cls ):
        
        cls._access_key = HydrusData.GenerateKey()
        
        cls._serverside_file_service = HydrusNetwork.GenerateService( HydrusData.GenerateKey(), HC.FILE_REPOSITORY, 'file repo', HC.DEFAULT_SERVICE_PORT + 1 )
        cls._serverside_tag_service = HydrusNetwork.GenerateService( HydrusData.GenerateKey(), HC.TAG_REPOSITORY, 'tag repo', HC.DEFAULT_SERVICE_PORT )
        cls._serverside_admin_service = HydrusNetwork.GenerateService( HydrusData.GenerateKey(), HC.SERVER_ADMIN, 'server admin', HC.DEFAULT_SERVER_ADMIN_PORT )
        
        cls._clientside_file_service = ClientServices.GenerateService( HydrusData.GenerateKey(), HC.FILE_REPOSITORY, 'file repo' )
        cls._clientside_tag_service = ClientServices.GenerateService( HydrusData.GenerateKey(), HC.TAG_REPOSITORY, 'tag repo' )
        cls._clientside_admin_service = ClientServices.GenerateService( HydrusData.GenerateKey(), HC.SERVER_ADMIN, 'server admin' )
        
        cls._clientside_file_service.SetCredentials( HydrusNetwork.Credentials( '127.0.0.1', HC.DEFAULT_SERVICE_PORT + 1, cls._access_key ) )
        cls._clientside_tag_service.SetCredentials( HydrusNetwork.Credentials( '127.0.0.1', HC.DEFAULT_SERVICE_PORT, cls._access_key ) )
        cls._clientside_admin_service.SetCredentials( HydrusNetwork.Credentials( '127.0.0.1', HC.DEFAULT_SERVER_ADMIN_PORT, cls._access_key ) )
        
        cls._local_booru = ClientServices.GenerateService( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, 'local booru' )
        
        services_manager = HG.test_controller.services_manager
        
        services_manager._keys_to_services[ cls._clientside_file_service.GetServiceKey() ] = cls._clientside_file_service
        services_manager._keys_to_services[ cls._clientside_tag_service.GetServiceKey() ] = cls._clientside_tag_service
        services_manager._keys_to_services[ cls._clientside_admin_service.GetServiceKey() ] = cls._clientside_admin_service
        
        permissions = [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ]
        
        account_key = HydrusData.GenerateKey()
        account_type = HydrusNetwork.AccountType.GenerateAdminAccountType( HC.SERVER_ADMIN )
        created = HydrusData.GetNow() - 100000
        expires = None
        
        cls._account = HydrusNetwork.Account( account_key, account_type, created, expires )
        
        cls._file_hash = HydrusData.GenerateKey()
        
        def TWISTEDSetup():
            
            cls._ssl_cert_path = os.path.join( TestController.DB_DIR, 'server.crt' )
            cls._ssl_key_path = os.path.join( TestController.DB_DIR, 'server.key' )
            
            # if db test ran, this is still hanging around and read-only, so don't bother to fail overwriting
            if not os.path.exists( cls._ssl_cert_path ):
                
                HydrusEncryption.GenerateOpenSSLCertAndKeyFile( cls._ssl_cert_path, cls._ssl_key_path )
                
            
            context_factory = twisted.internet.ssl.DefaultOpenSSLContextFactory( cls._ssl_key_path, cls._ssl_cert_path )
            
            reactor.listenSSL( HC.DEFAULT_SERVER_ADMIN_PORT, ServerServer.HydrusServiceAdmin( cls._serverside_admin_service ), context_factory )
            reactor.listenSSL( HC.DEFAULT_SERVICE_PORT + 1, ServerServer.HydrusServiceRepositoryFile( cls._serverside_file_service ), context_factory )
            reactor.listenSSL( HC.DEFAULT_SERVICE_PORT, ServerServer.HydrusServiceRepositoryTag( cls._serverside_tag_service ), context_factory )
            
            reactor.listenTCP( 45866, ClientLocalServer.HydrusServiceBooru( cls._local_booru, allow_non_local_connections = False ) )
            
        
        reactor.callFromThread( TWISTEDSetup )
        
        time.sleep( 1 )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        for path in ( cls._ssl_cert_path, cls._ssl_key_path ):
            
            HydrusPaths.MakeFileWritable( path )
            
            os.unlink( path )
            
        
    
    def _test_basics( self, host, port, https = True ):
        
        if https:
            
            context = ssl.SSLContext( ssl.PROTOCOL_SSLv23 )
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            
            connection = http.client.HTTPSConnection( host, port, timeout = 10, context = context )
            
        else:
            
            connection = http.client.HTTPConnection( host, port, timeout = 10 )
            
        
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
        
    
    def _test_file_repo( self, service ):
        
        # file
        
        path = ServerFiles.GetExpectedFilePath( self._file_hash )
        
        HydrusPaths.MakeSureDirectoryExists( os.path.dirname( path ) )
        
        with open( path, 'wb' ) as f:
            
            f.write( EXAMPLE_FILE )
            
        
        response = service.Request( HC.GET, 'file', { 'hash' : self._file_hash } )
        
        self.assertEqual( response, EXAMPLE_FILE )
        
        try: os.remove( path )
        except: pass
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )
        
        with open( path, 'rb' ) as f:
            
            file_bytes = f.read()
            
        
        HG.test_controller.ClearWrites( 'file' )
        
        service.Request( HC.POST, 'file', { 'file' : file_bytes } )
        
        written = HG.test_controller.GetWrite( 'file' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_account, written_file_dict ) = args
        
        self.assertEqual( written_file_dict[ 'hash' ], b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3' )
        self.assertEqual( written_file_dict[ 'ip' ], '127.0.0.1' )
        self.assertEqual( written_file_dict[ 'height' ], 200 )
        self.assertEqual( written_file_dict[ 'width' ], 200 )
        self.assertEqual( written_file_dict[ 'mime' ], 2 )
        self.assertEqual( written_file_dict[ 'size' ], 5270 )
        
        # ip
        
        ( ip, timestamp ) = ( '94.45.87.123', HydrusData.GetNow() - 100000 )
        
        HG.test_controller.SetRead( 'ip', ( ip, timestamp ) )
        
        response = service.Request( HC.GET, 'ip', { 'hash' : self._file_hash } )
        
        self.assertEqual( response[ 'ip' ], ip )
        self.assertEqual( response[ 'timestamp' ], timestamp )
        
        # thumbnail
        
        path = ServerFiles.GetExpectedThumbnailPath( self._file_hash )
        
        HydrusPaths.MakeSureDirectoryExists( os.path.dirname( path ) )
        
        with open( path, 'wb' ) as f:
            
            f.write( EXAMPLE_THUMBNAIL )
            
        
        response = service.Request( HC.GET, 'thumbnail', { 'hash' : self._file_hash } )
        
        self.assertEqual( response, EXAMPLE_THUMBNAIL )
        
        try: os.remove( path )
        except: pass
        
    
    def _test_local_booru( self, host, port ):
        
        #
        
        connection = http.client.HTTPConnection( host, port, timeout = 10 )
        
        #
        
        with open( os.path.join( HC.STATIC_DIR, 'local_booru_style.css' ), 'rb' ) as f:
            
            css = f.read()
            
        
        connection.request( 'GET', '/style.css' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, css )
        
        #
        
        share_key = HydrusData.GenerateKey()
        hashes = [ HydrusData.GenerateKey() for i in range( 5 ) ]
        
        client_files_default = os.path.join( TestController.DB_DIR, 'client_files' )
        
        hash_encoded = hashes[0].hex()
        
        prefix = hash_encoded[:2]
        
        file_path =  os.path.join( client_files_default, 'f' + prefix, hash_encoded + '.jpg' )
        thumbnail_path = os.path.join( client_files_default, 't' + prefix, hash_encoded + '.thumbnail' )
        
        with open( file_path, 'wb' ) as f:
            
            f.write( EXAMPLE_FILE )
            
        
        with open( thumbnail_path, 'wb' ) as f:
            
            f.write( EXAMPLE_THUMBNAIL )
            
        
        local_booru_manager = HG.client_controller.local_booru_manager
        
        #
        
        self._test_local_booru_requests( connection, share_key, hashes[0], 404 )
        
        #
        
        info = {}
        info[ 'name' ] = 'name'
        info[ 'text' ] = 'text'
        info[ 'timeout' ] = 0
        info[ 'hashes' ] = hashes
        
        file_info_manager = ClientMedia.FileInfoManager( 1, hashes[0], 500, HC.IMAGE_JPEG, 640, 480 )
        
        file_viewing_stats_manager = ClientMedia.FileViewingStatsManager.STATICGenerateEmptyManager()
        
        media_results = [ ClientMedia.MediaResult( file_info_manager, ClientMedia.TagsManager( {} ), ClientMedia.LocationsManager( set(), set(), set(), set() ), ClientRatings.RatingsManager( {} ), file_viewing_stats_manager ) for hash in hashes ]
        
        HG.test_controller.SetRead( 'local_booru_share_keys', [ share_key ] )
        HG.test_controller.SetRead( 'local_booru_share', info )
        HG.test_controller.SetRead( 'media_results', media_results )
        
        local_booru_manager.RefreshShares()
        
        #
        
        self._test_local_booru_requests( connection, share_key, hashes[0], 403 )
        
        #
        
        info[ 'timeout' ] = None
        HG.test_controller.SetRead( 'local_booru_share', info )
        
        local_booru_manager.RefreshShares()
        
        #
        
        self._test_local_booru_requests( connection, share_key, hashes[0], 200 )
        
        #
        
        HG.test_controller.SetRead( 'local_booru_share_keys', [] )
        
        local_booru_manager.RefreshShares()
        
        #
        
        self._test_local_booru_requests( connection, share_key, hashes[0], 404 )
        
    
    def _test_local_booru_requests( self, connection, share_key, hash, expected_result ):
        
        requests = []
        
        requests.append( '/gallery?share_key=' + share_key.hex() )
        requests.append( '/page?share_key=' + share_key.hex() + '&hash=' + hash.hex() )
        requests.append( '/file?share_key=' + share_key.hex() + '&hash=' + hash.hex() )
        requests.append( '/thumbnail?share_key=' + share_key.hex() + '&hash=' + hash.hex() )
        
        for request in requests:
            
            connection.request( 'GET', request )
            
            response = connection.getresponse()
            
            data = response.read()
            
            self.assertEqual( response.status, expected_result )
            
        
    
    def _test_repo( self, service ):
        
        service_key = service.GetServiceKey()
        
        # num_petitions
        
        num_petitions = [ [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED, 23 ], [ HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING, 0 ] ]
        
        HG.test_controller.SetRead( 'num_petitions', num_petitions )
        
        response = service.Request( HC.GET, 'num_petitions' )
        
        self.assertEqual( response[ 'num_petitions' ], num_petitions )
        
        # petition
        
        action = HC.CONTENT_UPDATE_PETITION
        petitioner_account = HydrusNetwork.Account.GenerateUnknownAccount()
        reason = 'it sucks'
        contents = [ HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, [ HydrusData.GenerateKey() for i in range( 10 ) ] ) ]
        
        petition = HydrusNetwork.Petition( action, petitioner_account, reason, contents )
        
        HG.test_controller.SetRead( 'petition', petition )
        
        response = service.Request( HC.GET, 'petition', { 'content_type' : HC.CONTENT_TYPE_FILES, 'status' : HC.CONTENT_UPDATE_PETITION } )
        
        self.assertEqual( response[ 'petition' ].GetSerialisableTuple(), petition.GetSerialisableTuple() )
        
        # definitions
        
        definitions_update = HydrusNetwork.DefinitionsUpdate()
        
        for i in range( 100, 200 ):
            
            definitions_update.AddRow( ( HC.DEFINITIONS_TYPE_TAGS, i, 'series:test ' + str( i ) ) )
            definitions_update.AddRow( ( HC.DEFINITIONS_TYPE_HASHES, i + 500, HydrusData.GenerateKey() ) )
            
        
        definitions_update_network_bytes = definitions_update.DumpToNetworkBytes()
        
        definitions_update_hash = hashlib.sha256( definitions_update_network_bytes ).digest()
        
        path = ServerFiles.GetExpectedFilePath( definitions_update_hash )
        
        HydrusPaths.MakeSureDirectoryExists( path )
        
        with open( path, 'wb' ) as f:
            
            f.write( definitions_update_network_bytes )
            
        
        response = service.Request( HC.GET, 'update', { 'update_hash' : definitions_update_hash } )
        
        try: os.remove( path )
        except: pass
        
        self.assertEqual( response, definitions_update_network_bytes )
        
        # content
        
        rows = [ ( random.randint( 100, 1000 ), [ random.randint( 100, 1000 ) for i in range( 50 ) ] ) for j in range( 20 ) ]
        
        content_update = HydrusNetwork.ContentUpdate()
        
        for row in rows:
            
            content_update.AddRow( ( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, row ) )
            
        
        content_update_network_bytes = content_update.DumpToNetworkBytes()
        
        content_update_hash = hashlib.sha256( content_update_network_bytes ).digest()
        
        path = ServerFiles.GetExpectedFilePath( content_update_hash )
        
        with open( path, 'wb' ) as f:
            
            f.write( content_update_network_bytes )
            
        
        response = service.Request( HC.GET, 'update', { 'update_hash' : content_update_hash } )
        
        try: os.remove( path )
        except: pass
        
        self.assertEqual( response, content_update_network_bytes )
        
        # metadata
        
        metadata = HydrusNetwork.Metadata()
        
        metadata.AppendUpdate( [ definitions_update_hash, content_update_hash ], HydrusData.GetNow() - 101000, HydrusData.GetNow() - 1000, HydrusData.GetNow() + 100000 )
        
        service._metadata = metadata
        
        response = service.Request( HC.GET, 'metadata_slice', { 'since' : 0 } )
        
        self.assertEqual( response[ 'metadata_slice' ].GetSerialisableTuple(), metadata.GetSerialisableTuple() )
        
        # post content
        
        raise NotImplementedError()
        '''
        update = HydrusData.ClientToServerContentUpdatePackage( {}, hash_ids_to_hashes )
        
        HG.test_controller.ClearWrites( 'update' )
        
        service.Request( HC.POST, 'content_update_package', { 'update' : update } )
        
        written = HG.test_controller.GetWrite( 'update' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_account, written_update ) = args
        
        self.assertEqual( update.GetHashes(), written_update.GetHashes() )
        '''
    
    def _test_restricted( self, service ):
        
        # access_key
        
        registration_key = HydrusData.GenerateKey()
        
        HG.test_controller.SetRead( 'access_key', self._access_key )
        
        response = service.Request( HC.GET, 'access_key', { 'registration_key' : registration_key } )
        
        self.assertEqual( response[ 'access_key' ], self._access_key )
        
        # set up session
        
        last_error = 0
        
        account = self._account
        
        HG.test_controller.SetRead( 'service', service )
        
        HG.test_controller.SetRead( 'account_key_from_access_key', HydrusData.GenerateKey() )
        HG.test_controller.SetRead( 'account', self._account )
        
        # account
        
        response = service.Request( HC.GET, 'account' )
        
        self.assertEqual( repr( response[ 'account' ] ), repr( self._account ) )
        
        # account_info
        
        account_info = { 'message' : 'hello' }
        
        HG.test_controller.SetRead( 'account_info', account_info )
        HG.test_controller.SetRead( 'account_key_from_identifier', HydrusData.GenerateKey() )
        
        response = service.Request( HC.GET, 'account_info', { 'subject_account_key' : HydrusData.GenerateKey() } )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        # this not working for now, screw it m8
        
        #response = service.Request( HC.GET, 'account_info', { 'subject_hash' : HydrusData.GenerateKey() } )
        
        #self.assertEqual( response[ 'account_info' ], account_info )
        
        #response = service.Request( HC.GET, 'account_info', { 'subject_hash' : HydrusData.GenerateKey(), 'subject_tag' : 'hello' } )
        
        #self.assertEqual( response[ 'account_info' ], account_info )
        
        # account_types
        
        account_types = [ HydrusNetwork.AccountType.GenerateAdminAccountType( service.GetServiceType() ) ]
        
        HG.test_controller.SetRead( 'account_types', account_types )
        
        HG.test_controller.ClearWrites( 'account_types' )
        
        response = service.Request( HC.GET, 'account_types' )
        
        self.assertEqual( response[ 'account_types' ][0].GetAccountTypeKey(), account_types[0].GetAccountTypeKey() )
        
        service.Request( HC.POST, 'account_types', { 'account_types' : account_types, 'deletee_account_type_keys_to_new_account_type_keys' : {} } )
        
        written = HG.test_controller.GetWrite( 'account_types' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_account, written_account_types, written_deletee_account_type_keys_to_new_account_type_keys ) = args
        
        self.assertEqual( written_account_types[0].GetAccountTypeKey(), account_types[0].GetAccountTypeKey() )
        self.assertEqual( written_deletee_account_type_keys_to_new_account_type_keys, {} )
        
        # registration_keys
        
        registration_key = HydrusData.GenerateKey()
        
        HG.test_controller.SetRead( 'registration_keys', [ registration_key ] )
        
        response = service.Request( HC.GET, 'registration_keys', { 'num' : 1, 'account_type_key' : os.urandom( 32 ), 'expires' : HydrusData.GetNow() + 1200 } )
        
        self.assertEqual( response[ 'registration_keys' ], [ registration_key ] )
        
    
    def _test_server_admin( self, service ):
        
        # init
        
        access_key = HydrusData.GenerateKey()
        
        HG.test_controller.SetRead( 'access_key', access_key )
        
        response = service.Request( HC.GET, 'access_key', { 'registration_key' : b'init' } )
        
        self.assertEqual( response[ 'access_key' ], access_key )
        
        #
        
        ## backup
        
        response = service.Request( HC.POST, 'backup' )
        
        #
        
        # add some new services info
        
    
    def _test_tag_repo( self, service ):
        
        pass
        
    
    def test_repository_file( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVICE_PORT
        
        self._test_basics( host, port )
        self._test_restricted( self._clientside_file_service )
        # broke since service rewrite
        #self._test_repo( self._clientside_file_service )
        #self._test_file_repo( self._clientside_file_service )
        
    
    def test_repository_tag( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVICE_PORT + 1
        
        self._test_basics( host, port )
        self._test_restricted( self._clientside_tag_service )
        # broke since service rewrite
        #self._test_repo( self._clientside_tag_service )
        #self._test_tag_repo( self._clientside_tag_service )
        
    
    def test_server_admin( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVER_ADMIN_PORT
        
        self._test_basics( host, port )
        self._test_restricted( self._clientside_admin_service )
        self._test_server_admin( self._clientside_admin_service )
        
    
    def test_local_booru( self ):
        
        host = '127.0.0.1'
        port = 45866
        
        self._test_basics( host, port, https = False )
        self._test_local_booru( host, port )
        
    
    '''
class TestAMP( unittest.TestCase ):
    
    @classmethod
    def setUpClass( cls ):
        
        cls._alice = HydrusData.GenerateKey()
        cls._bob = HydrusData.GenerateKey()
        
        cls._server_port = HC.DEFAULT_SERVICE_PORT + 10
        
        cls._service_key = HydrusData.GenerateKey()
        
        def TWISTEDSetup():
            
            cls._factory = HydrusServer.MessagingServiceFactory( cls._service_key )
            
            reactor.listenTCP( cls._server_port, cls._factory )
            
        
        reactor.callFromThread( TWISTEDSetup )
        
        time.sleep( 1 )
        
    
    def _get_deferred_result( self, deferred ):
        
        def err( failure ):
            
            failure.trap( Exception )
            
            return failure.type( failure.value )
            
        
        deferred.addErrback( err )
        
        before = time.time()
        
        while not deferred.called:
            
            time.sleep( 0.1 )
            
            if time.time() - before > 10: raise Exception( 'Trying to get deferred timed out!' )
            
        
        result = deferred.result
        
        if issubclass( type( result ), Exception ): raise result
        
        return result
        
    
    def _get_client_protocol( self ):
        
        point = TCP4ClientEndpoint( reactor, '127.0.0.1', self._server_port )
        
        deferred = connectProtocol( point, HydrusServerAMP.MessagingClientProtocol() )
        
        protocol = self._get_deferred_result( deferred )
        
        return protocol
        
    
    def _make_persistent_connection( self, protocol, access_key, name ):
        
        identifier = hashlib.sha256( access_key ).digest()
        
        HC.app.SetRead( 'im_identifier', identifier )
        
        permissions = [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ]
        
        account_key = HydrusData.GenerateKey()
        account_type = HC.AccountType( 'account', permissions, ( None, None ) )
        created = HC.GetNow() - 100000
        expires = None
        used_bytes = 0
        used_requests = 0
        
        account = HC.Account( account_key, account_type, created, expires, used_bytes, used_requests )
        
        HC.app.SetRead( 'account_key_from_access_key', HydrusData.GenerateKey() )
        HC.app.SetRead( 'account', account )
        
        deferred = protocol.callRemote( HydrusServerAMP.IMSessionKey, access_key = access_key, name = name )
        
        result = self._get_deferred_result( deferred )
        
        session_key = result[ 'session_key' ]
        
        deferred = protocol.callRemote( HydrusServerAMP.IMLoginPersistent, network_version = HC.NETWORK_VERSION, session_key = session_key )
        
        result = self._get_deferred_result( deferred )
        
        self.assertEqual( result, {} )
        
    
    def _make_temporary_connection( self, protocol, identifier, name ):
        
        deferred = protocol.callRemote( HydrusServerAMP.IMLoginTemporary, network_version = HC.NETWORK_VERSION, identifier = identifier, name = name )
        
        result = self._get_deferred_result( deferred )
        
        self.assertEqual( result, {} )
        
    
    def test_connections( self ):
        
        persistent_protocol = self._get_client_protocol()
        persistent_access_key = HydrusData.GenerateKey()
        persistent_identifier = hashlib.sha256( persistent_access_key ).digest()
        persistent_name = 'persistent'
        
        self._make_persistent_connection( persistent_protocol, persistent_access_key, persistent_name )
        
        self.assertIn( persistent_identifier, self._factory._persistent_connections )
        self.assertIn( persistent_name, self._factory._persistent_connections[ persistent_identifier ] )
        
        temp_protocol_1 = self._get_client_protocol()
        temp_protocol_2 = self._get_client_protocol()
        temp_name_1 = 'temp_1'
        temp_identifier = HydrusData.GenerateKey()
        temp_name_2 = 'temp_2'
        
        self._make_temporary_connection( temp_protocol_1, temp_identifier, temp_name_1 )
        self._make_temporary_connection( temp_protocol_2, temp_identifier, temp_name_2 )
        
        self.assertIn( temp_identifier, self._factory._temporary_connections )
        self.assertIn( temp_name_1, self._factory._temporary_connections[ temp_identifier ] )
        self.assertIn( temp_name_2, self._factory._temporary_connections[ temp_identifier ] )
        
    
    def test_status( self ):
        
        # some of this is UDP, so get that working!
        
        # add two bobs
        
        # ask for status of the bobs
        # test that we get both, online
        
        # now disconnect a bob
        # ask for bob status
        # test that we only have one bob
        
        # now disconnect other bob
        # repeat for nothing
        
        pass
        
    
    def test_message( self ):
        
        persistent_protocol = self._get_client_protocol()
        persistent_access_key = HydrusData.GenerateKey()
        persistent_identifier = hashlib.sha256( persistent_access_key ).digest()
        persistent_name = 'persistent'
        
        self._make_persistent_connection( persistent_protocol, persistent_access_key, persistent_name )
        
        temp_protocol = self._get_client_protocol()
        temp_identifier = HydrusData.GenerateKey()
        temp_name = 'temp'
        
        self._make_temporary_connection( temp_protocol, temp_identifier, temp_name )
        
        #
        
        HC.pubsub.ClearPubSubs()
        
        message = 'hello temp'
        
        deferred = persistent_protocol.callRemote( HydrusServerAMP.IMMessageServer, identifier_to = temp_identifier, name_to = temp_name, message = message )
        
        result = self._get_deferred_result( deferred )
        
        self.assertEqual( result, {} )
        
        result = HC.pubsub.GetPubSubs( 'im_message_received' )
        
        [ ( args, kwargs ) ] = result
        
        self.assertEqual( args, ( persistent_identifier, persistent_name, temp_identifier, temp_name, message ) )
        
        #
        
        HC.pubsub.ClearPubSubs()
        
        message = 'hello persistent'
        
        deferred = temp_protocol.callRemote( HydrusServerAMP.IMMessageServer, identifier_to = persistent_identifier, name_to = persistent_name, message = message )
        
        result = self._get_deferred_result( deferred )
        
        self.assertEqual( result, {} )
        
        result = HC.pubsub.GetPubSubs( 'im_message_received' )
        
        [ ( args, kwargs ) ] = result
        
        self.assertEqual( args, ( temp_identifier, temp_name, persistent_identifier, persistent_name, message ) )
        '''
