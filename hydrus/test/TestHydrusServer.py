import hashlib
import http.client
import os
import random
import ssl
import time
import typing
import unittest

from twisted.internet import reactor

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusEncryption
from hydrus.core import HydrusPaths
from hydrus.core import HydrusStaticDir
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworking

from hydrus.client import ClientServices

from hydrus.server import ServerFiles
from hydrus.server.networking import ServerServer

from hydrus.test import TestController
from hydrus.test import TestGlobals as TG


with open( HydrusStaticDir.GetStaticPath( 'hydrus.png' ), 'rb' ) as f_g:
    
    EXAMPLE_FILE = f_g.read()
    

with open( HydrusStaticDir.GetStaticPath( 'hydrus_small.png' ), 'rb' ) as f_g:
    
    EXAMPLE_THUMBNAIL = f_g.read()
    

class TestServer( unittest.TestCase ):
    
    _access_key: bytes = HydrusData.GenerateKey()
    
    _serverside_file_service: typing.Any = None
    _serverside_tag_service: typing.Any = None
    _serverside_admin_service: typing.Any = None
    
    _clientside_file_service: typing.Any = None
    _clientside_tag_service: typing.Any = None
    _clientside_admin_service: typing.Any = None
    
    _ssl_cert_path: str = ''
    _ssl_key_path: str = ''
    
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
        
        services_manager = TG.test_controller.services_manager
        
        services_manager._keys_to_services[ cls._clientside_file_service.GetServiceKey() ] = cls._clientside_file_service
        services_manager._keys_to_services[ cls._clientside_tag_service.GetServiceKey() ] = cls._clientside_tag_service
        services_manager._keys_to_services[ cls._clientside_admin_service.GetServiceKey() ] = cls._clientside_admin_service
        
        account_key = HydrusData.GenerateKey()
        account_type = HydrusNetwork.AccountType.GenerateAdminAccountType( HC.SERVER_ADMIN )
        created = HydrusTime.GetNow() - 100000
        expires = None
        
        cls._account = HydrusNetwork.Account( account_key, account_type, created, expires )
        
        cls._service_keys_to_empty_account_types = {}
        cls._service_keys_to_empty_accounts = {}
        
        cls._file_hash = HydrusData.GenerateKey()
        
        def TWISTEDSetup():
            
            cls._ssl_cert_path = os.path.join( TestController.DB_DIR, 'server.crt' )
            cls._ssl_key_path = os.path.join( TestController.DB_DIR, 'server.key' )
            
            # if db test ran, this is still hanging around and read-only, so don't bother to fail overwriting
            if not os.path.exists( cls._ssl_cert_path ):
                
                HydrusEncryption.GenerateOpenSSLCertAndKeyFile( cls._ssl_cert_path, cls._ssl_key_path )
                
            
            from hydrus.core.networking import HydrusServerContextFactory
            
            context_factory = HydrusServerContextFactory.GenerateSSLContextFactory( cls._ssl_cert_path, cls._ssl_key_path )
            
            reactor.listenSSL( HC.DEFAULT_SERVER_ADMIN_PORT, ServerServer.HydrusServiceAdmin( cls._serverside_admin_service ), context_factory )
            reactor.listenSSL( HC.DEFAULT_SERVICE_PORT + 1, ServerServer.HydrusServiceRepositoryFile( cls._serverside_file_service ), context_factory )
            reactor.listenSSL( HC.DEFAULT_SERVICE_PORT, ServerServer.HydrusServiceRepositoryTag( cls._serverside_tag_service ), context_factory )
            
        
        reactor.callFromThread( TWISTEDSetup )
        
        time.sleep( 3 )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        for path in ( cls._ssl_cert_path, cls._ssl_key_path ):
            
            if HC.PLATFORM_WINDOWS:
                
                path_stat = os.stat( path )
                
                # this can be needed on a Windows device
                HydrusPaths.TryToMakeFileWriteable( path, path_stat )
                
            
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
        
        with open( HydrusStaticDir.GetStaticPath( 'hydrus.ico' ), 'rb' ) as f:
            
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
        
        try:
            
            os.remove( path )
            
        except Exception as e:
            
            pass
            
        
        #
        
        path = HydrusStaticDir.GetStaticPath( 'hydrus.png' )
        
        TG.test_controller.ClearWrites( 'file' )
        
        service.Request( HC.POST, 'file', file_body_path = path )
        
        written = TG.test_controller.GetWrite( 'file' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_account, written_file_dict ) = args
        
        hash = b'\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3'
        
        self.assertEqual( written_file_dict[ 'hash' ], hash )
        self.assertEqual( written_file_dict[ 'ip' ], '127.0.0.1' )
        self.assertEqual( written_file_dict[ 'height' ], 200 )
        self.assertEqual( written_file_dict[ 'width' ], 200 )
        self.assertEqual( written_file_dict[ 'mime' ], 2 )
        self.assertEqual( written_file_dict[ 'size' ], 5270 )
        
        # ip
        
        ( ip, timestamp ) = ( '94.45.87.123', HydrusTime.GetNow() - 100000 )
        
        TG.test_controller.SetRead( 'ip', ( ip, timestamp ) )
        
        response = service.Request( HC.GET, 'ip', { 'hash' : self._file_hash } )
        
        self.assertEqual( response[ 'ip' ], ip )
        self.assertEqual( response[ 'timestamp' ], timestamp )
        
        # account key from file
        
        test_hash = HydrusData.GenerateKey()
        
        TG.test_controller.SetRead( 'account_key_from_content', self._account.GetAccountKey() )
        
        content = HydrusNetwork.Content( content_type = HC.CONTENT_TYPE_FILES, content_data = ( test_hash, ) )
        
        response = service.Request( HC.GET, 'account_key_from_content', { 'subject_content' : content } )
        
        self.assertEqual( repr( response[ 'subject_account_key' ] ), repr( self._account.GetAccountKey() ) )
        
        # thumbnail
        
        path = ServerFiles.GetExpectedThumbnailPath( self._file_hash )
        
        HydrusPaths.MakeSureDirectoryExists( os.path.dirname( path ) )
        
        with open( path, 'wb' ) as f:
            
            f.write( EXAMPLE_THUMBNAIL )
            
        
        response = service.Request( HC.GET, 'thumbnail', { 'hash' : self._file_hash } )
        
        self.assertEqual( response, EXAMPLE_THUMBNAIL )
        
        try:
            
            os.remove( path )
            
        except Exception as e:
            
            pass
            
        
    
    def _test_repo( self, service ):
        
        service_key = service.GetServiceKey()
        
        # num_petitions
        
        num_petitions = [ [ HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_STATUS_PETITIONED, 23 ], [ HC.CONTENT_TYPE_TAG_PARENTS, HC.CONTENT_STATUS_PENDING, 0 ] ]
        
        TG.test_controller.SetRead( 'num_petitions', num_petitions )
        
        response = service.Request( HC.GET, 'num_petitions' )
        
        self.assertEqual( response[ 'num_petitions' ], num_petitions )
        
        # petition
        
        petitioner_account = HydrusNetwork.Account.GenerateUnknownAccount( HydrusData.GenerateKey() )
        reason = 'it sucks'
        actions_and_contents = ( HC.CONTENT_UPDATE_PETITION, [ HydrusNetwork.Content( HC.CONTENT_TYPE_FILES, [ HydrusData.GenerateKey() for i in range( 10 ) ] ) ] )
        
        petition_header = HydrusNetwork.PetitionHeader(
            content_type = HC.CONTENT_TYPE_FILES,
            status = HC.CONTENT_STATUS_PETITIONED,
            account_key = petitioner_account.GetAccountKey(),
            reason = reason
        )
        
        petition = HydrusNetwork.Petition( petitioner_account = petitioner_account, petition_header = petition_header, actions_and_contents = actions_and_contents )
        
        TG.test_controller.SetRead( 'petition', petition )
        
        response = service.Request( HC.GET, 'petition', { 'content_type' : HC.CONTENT_TYPE_FILES, 'status' : HC.CONTENT_UPDATE_PETITION } )
        
        self.assertEqual( response[ 'petition' ].GetSerialisableTuple(), petition.GetSerialisableTuple() )
        
        TG.test_controller.SetRead( 'petition', petition )
        
        response = service.Request( HC.GET, 'petition', { 'content_type' : HC.CONTENT_TYPE_FILES, 'status' : HC.CONTENT_UPDATE_PETITION, 'account_key' : petitioner_account.GetAccountKey(), reason : reason } )
        
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
        
        try:
            
            os.remove( path )
            
        except Exception as e:
            
            pass
            
        
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
        
        try:
            
            os.remove( path )
            
        except Exception as e:
            
            pass
            
        
        self.assertEqual( response, content_update_network_bytes )
        
        # metadata
        
        metadata = HydrusNetwork.Metadata()
        
        metadata.AppendUpdate( [ definitions_update_hash, content_update_hash ], HydrusTime.GetNow() - 101000, HydrusTime.GetNow() - 1000, HydrusTime.GetNow() + 100000 )
        
        service._metadata = metadata
        
        response = service.Request( HC.GET, 'metadata_slice', { 'since' : 0 } )
        
        self.assertEqual( response[ 'metadata_slice' ].GetSerialisableTuple(), metadata.GetSerialisableTuple() )
        
        # post content
        
        raise NotImplementedError()
        '''
        update = HydrusData.ClientToServerContentUpdatePackage( {}, hash_ids_to_hashes )
        
        TG.test_controller.ClearWrites( 'update' )
        
        service.Request( HC.POST, 'content_update_package', { 'update' : update } )
        
        written = TG.test_controller.GetWrite( 'update' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_account, written_update ) = args
        
        self.assertEqual( update.GetHashes(), written_update.GetHashes() )
        '''
    
    def _test_restricted( self, service ):
        
        # access_key
        
        registration_key = HydrusData.GenerateKey()
        
        TG.test_controller.SetRead( 'access_key', self._access_key )
        
        response = service.Request( HC.GET, 'access_key', { 'registration_key' : registration_key } )
        
        self.assertEqual( response[ 'access_key' ], self._access_key )
        
        # set up session
        
        last_error = 0
        
        account = self._account
        
        TG.test_controller.SetRead( 'service', service )
        
        TG.test_controller.SetRead( 'account_key_from_access_key', HydrusData.GenerateKey() )
        TG.test_controller.SetRead( 'account', self._account )
        
        # account
        
        response = service.Request( HC.GET, 'account' )
        
        self.assertEqual( repr( response[ 'account' ] ), repr( self._account ) )
        
        # account from access key
        
        TG.test_controller.SetRead( 'account', self._account )
        
        response = service.Request( HC.GET, 'other_account', { 'subject_account_key' : self._account.GetAccountKey() } )
        
        self.assertEqual( repr( response[ 'account' ] ), repr( self._account ) )
        
        # account_info
        
        account_info = { 'message' : 'hello' }
        
        TG.test_controller.SetRead( 'account_info', account_info )
        
        response = service.Request( HC.GET, 'account_info', { 'subject_account_key' : HydrusData.GenerateKey() } )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        # account_types
        
        account_types = [ HydrusNetwork.AccountType.GenerateAdminAccountType( service.GetServiceType() ) ]
        
        TG.test_controller.SetRead( 'account_types', account_types )
        
        TG.test_controller.ClearWrites( 'account_types' )
        
        response = service.Request( HC.GET, 'account_types' )
        
        self.assertEqual( response[ 'account_types' ][0].GetAccountTypeKey(), account_types[0].GetAccountTypeKey() )
        
        empty_account_type = HydrusNetwork.AccountType.GenerateNewAccountType( 'empty account', {}, HydrusNetworking.BandwidthRules() )
        
        account_types.append( empty_account_type )
        
        service.Request( HC.POST, 'account_types', { 'account_types' : account_types, 'deletee_account_type_keys_to_new_account_type_keys' : {} } )
        
        written = TG.test_controller.GetWrite( 'account_types' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_account, written_account_types, written_deletee_account_type_keys_to_new_account_type_keys ) = args
        
        self.assertEqual( { wat.GetAccountTypeKey() for wat in written_account_types }, { at.GetAccountTypeKey() for at in account_types } )
        self.assertEqual( written_deletee_account_type_keys_to_new_account_type_keys, {} )
        
        # registration_keys
        
        registration_key = HydrusData.GenerateKey()
        
        TG.test_controller.SetRead( 'registration_keys', [ registration_key ] )
        
        response = service.Request( HC.GET, 'registration_keys', { 'num' : 1, 'account_type_key' : os.urandom( 32 ), 'expires' : HydrusTime.GetNow() + 1200 } )
        
        self.assertEqual( response[ 'registration_keys' ], [ registration_key ] )
        
    
    def _test_server_admin( self, service ):
        
        # init
        
        access_key = HydrusData.GenerateKey()
        
        TG.test_controller.SetRead( 'access_key', access_key )
        
        response = service.Request( HC.GET, 'access_key', { 'registration_key' : b'init' } )
        
        self.assertEqual( response[ 'access_key' ], access_key )
        
        #
        
        response = service.Request( HC.GET, 'busy' )
        
        self.assertEqual( response, b'0' )
        
        response = service.Request( HC.POST, 'lock_on' )
        
        response = service.Request( HC.GET, 'busy' )
        
        self.assertEqual( response, b'1' )
        
        response = service.Request( HC.POST, 'lock_off' )
        
        response = service.Request( HC.GET, 'busy' )
        
        self.assertEqual( response, b'0' )
        
        #
        
        response = service.Request( HC.POST, 'backup' )
        response = service.Request( HC.POST, 'vacuum' )
        
        #
        
        # add some new services info
        
    
    def _test_tag_repo( self, service ):
        
        # account from mapping
        
        test_tag = 'character:samus aran'
        test_hash = HydrusData.GenerateKey()
        
        TG.test_controller.SetRead( 'account_key_from_content', self._account.GetAccountKey() )
        
        content = HydrusNetwork.Content( content_type = HC.CONTENT_TYPE_MAPPING, content_data = ( test_tag, test_hash ) )
        
        response = service.Request( HC.GET, 'account_key_from_content', { 'subject_content' : content } )
        
        self.assertEqual( repr( response[ 'subject_account_key' ] ), repr( self._account.GetAccountKey() ) )
        
    
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
