import ClientConstants as CC
import ClientData
import ClientFiles
import ClientLocalServer
import ClientMedia
import hashlib
import httplib
import HydrusConstants as HC
import HydrusEncryption
import HydrusPaths
import HydrusServer
import HydrusServerResources
import HydrusSerialisable
import itertools
import os
import ServerFiles
import ServerServer
import shutil
import ssl
import stat
import TestConstants
import time
import threading
import unittest
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.defer import deferredGenerator, waitForDeferred
import twisted.internet.ssl
import HydrusData
import HydrusGlobals

with open( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), 'rb' ) as f:
    
    EXAMPLE_FILE = f.read()
    
with open( os.path.join( HC.STATIC_DIR, 'hydrus_small.png' ), 'rb' ) as f:
    
    EXAMPLE_THUMBNAIL = f.read()
    
class TestServer( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        services = []
        
        self._file_service = ClientData.GenerateService( HydrusData.GenerateKey(), HC.FILE_REPOSITORY, 'file repo', {} )
        self._tag_service = ClientData.GenerateService( HydrusData.GenerateKey(), HC.TAG_REPOSITORY, 'tag repo', {} )
        self._admin_service = ClientData.GenerateService( HydrusData.GenerateKey(), HC.SERVER_ADMIN, 'server admin', {} )
        
        services_manager = HydrusGlobals.test_controller.GetServicesManager()
        
        services_manager._keys_to_services[ self._file_service.GetServiceKey() ] = self._file_service
        services_manager._keys_to_services[ self._tag_service.GetServiceKey() ] = self._tag_service
        services_manager._keys_to_services[ self._admin_service.GetServiceKey() ] = self._admin_service
        
        HydrusPaths.MakeSureDirectoryExists( ServerFiles.GetExpectedUpdateDir( self._file_service.GetServiceKey() ) )
        HydrusPaths.MakeSureDirectoryExists( ServerFiles.GetExpectedUpdateDir( self._tag_service.GetServiceKey() ) )
        
        permissions = [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ]
        
        account_key = HydrusData.GenerateKey()
        account_type = HydrusData.AccountType( 'account', permissions, ( None, None ) )
        created = HydrusData.GetNow() - 100000
        expires = None
        used_bytes = 0
        used_requests = 0
        
        self._account = HydrusData.Account( account_key, account_type, created, expires, used_bytes, used_requests )
        
        self._access_key = HydrusData.GenerateKey()
        self._file_hash = HydrusData.GenerateKey()
        
        def TWISTEDSetup():
            
            self._ssl_cert_path = os.path.join( TestConstants.DB_DIR, 'server.crt' )
            self._ssl_key_path = os.path.join( TestConstants.DB_DIR, 'server.key' )
            
            # if db test ran, this is still hanging around and read-only, so don't bother to fail overwriting
            if not os.path.exists( self._ssl_cert_path ):
                
                HydrusEncryption.GenerateOpenSSLCertAndKeyFile( self._ssl_cert_path, self._ssl_key_path )
                
            
            context_factory = twisted.internet.ssl.DefaultOpenSSLContextFactory( self._ssl_key_path, self._ssl_cert_path )
            
            reactor.listenSSL( HC.DEFAULT_SERVER_ADMIN_PORT, ServerServer.HydrusServiceAdmin( self._admin_service.GetServiceKey(), HC.SERVER_ADMIN, 'hello' ), context_factory )
            reactor.listenSSL( HC.DEFAULT_SERVICE_PORT, ServerServer.HydrusServiceRepositoryFile( self._file_service.GetServiceKey(), HC.FILE_REPOSITORY, 'hello' ), context_factory )
            reactor.listenSSL( HC.DEFAULT_SERVICE_PORT + 1, ServerServer.HydrusServiceRepositoryTag( self._tag_service.GetServiceKey(), HC.TAG_REPOSITORY, 'hello' ), context_factory )
            
            reactor.listenTCP( HC.DEFAULT_LOCAL_FILE_PORT, ClientLocalServer.HydrusServiceLocal( CC.COMBINED_LOCAL_FILE_SERVICE_KEY, HC.COMBINED_LOCAL_FILE, 'hello' ) )
            reactor.listenTCP( HC.DEFAULT_LOCAL_BOORU_PORT, ClientLocalServer.HydrusServiceBooru( CC.LOCAL_BOORU_SERVICE_KEY, HC.LOCAL_BOORU, 'hello' ) )
            
        
        reactor.callFromThread( TWISTEDSetup )
        
        time.sleep( 1 )
        
    
    def _test_basics( self, host, port, https = True ):
        
        if https:
            
            context = ssl.SSLContext( ssl.PROTOCOL_SSLv23 )
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            
            connection = httplib.HTTPSConnection( host, port, timeout = 10, context = context )
            
        else:
            
            connection = httplib.HTTPConnection( host, port, timeout = 10 )
            
        
        #
        
        connection.request( 'GET', '/' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        p1 = data == HydrusServerResources.CLIENT_ROOT_MESSAGE
        p2 = data == HydrusServerResources.ROOT_MESSAGE_BEGIN + 'hello' + HydrusServerResources.ROOT_MESSAGE_END
        
        self.assertTrue( p1 or p2 )
        
        #
        
        with open( os.path.join( HC.STATIC_DIR, 'hydrus.ico' ), 'rb' ) as f: favicon = f.read()
        
        connection.request( 'GET', '/favicon.ico' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, favicon )
        
    
    def _test_local_file( self, host, port ):
        
        connection = httplib.HTTPConnection( host, port, timeout = 10 )
        
        #
        
        client_files_default = os.path.join( TestConstants.DB_DIR, 'client_files' )

        hash_encoded = self._file_hash.encode( 'hex' )
        
        prefix = hash_encoded[:2]
        
        path =  os.path.join( client_files_default, 'f' + prefix, hash_encoded + '.jpg' )
        
        with open( path, 'wb' ) as f: f.write( EXAMPLE_FILE )
        
        connection.request( 'GET', '/file?hash=' + self._file_hash.encode( 'hex' ) )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, EXAMPLE_FILE )
        
        try: os.remove( path )
        except: pass
        
        #
        
        path = os.path.join( client_files_default, 't' + prefix, hash_encoded + '.thumbnail' )
        
        with open( path, 'wb' ) as f: f.write( EXAMPLE_THUMBNAIL )
        
        connection.request( 'GET', '/thumbnail?hash=' + self._file_hash.encode( 'hex' ) )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, EXAMPLE_THUMBNAIL )
        
        try: os.remove( path )
        except: pass
        
    
    def _test_file_repo( self, service, host, port ):
        
        info = service.GetInfo()
        
        info[ 'access_key' ] = self._access_key
        
        # file
        
        path = ServerFiles.GetExpectedFilePath( self._file_hash )
        
        HydrusPaths.MakeSureDirectoryExists( os.path.dirname( path ) )
        
        with open( path, 'wb' ) as f: f.write( EXAMPLE_FILE )
        
        response = service.Request( HC.GET, 'file', { 'hash' : self._file_hash.encode( 'hex' ) } )
        
        self.assertEqual( response, EXAMPLE_FILE )
        
        try: os.remove( path )
        except: pass
        
        path = os.path.join( HC.STATIC_DIR, 'hydrus.png' )

        with open( path, 'rb' ) as f: file = f.read()
        
        service.Request( HC.POST, 'file', { 'file' : file } )
        
        written = HydrusGlobals.test_controller.GetWrite( 'file' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_account, written_file_dict ) = args
        
        self.assertEqual( written_file_dict[ 'hash' ], '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3' )
        self.assertEqual( written_file_dict[ 'ip' ], '127.0.0.1' )
        self.assertEqual( written_file_dict[ 'height' ], 200 )
        self.assertEqual( written_file_dict[ 'width' ], 200 )
        self.assertEqual( written_file_dict[ 'mime' ], 2 )
        self.assertEqual( written_file_dict[ 'size' ], 5270 )
        
        # ip
        
        ( ip, timestamp ) = ( '94.45.87.123', HydrusData.GetNow() - 100000 )
        
        HydrusGlobals.test_controller.SetRead( 'ip', ( ip, timestamp ) )
        
        response = service.Request( HC.GET, 'ip', { 'hash' : self._file_hash.encode( 'hex' ) } )
        
        self.assertEqual( response[ 'ip' ], ip )
        self.assertEqual( response[ 'timestamp' ], timestamp )
        
        # thumbnail
        
        path = ServerFiles.GetExpectedThumbnailPath( self._file_hash )
        
        HydrusPaths.MakeSureDirectoryExists( os.path.dirname( path ) )
        
        with open( path, 'wb' ) as f: f.write( EXAMPLE_THUMBNAIL )
        
        response = service.Request( HC.GET, 'thumbnail', { 'hash' : self._file_hash.encode( 'hex' ) } )
        
        self.assertEqual( response, EXAMPLE_THUMBNAIL )
        
        try: os.remove( path )
        except: pass
        
    
    def _test_local_booru( self, host, port ):
        
        #
        
        connection = httplib.HTTPConnection( host, port, timeout = 10 )
        
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
        
        client_files_default = os.path.join( TestConstants.DB_DIR, 'client_files' )
        
        hash_encoded = hashes[0].encode( 'hex' )
        
        prefix = hash_encoded[:2]
        
        file_path =  os.path.join( client_files_default, 'f' + prefix, hash_encoded + '.jpg' )
        thumbnail_path = os.path.join( client_files_default, 't' + prefix, hash_encoded + '.thumbnail' )
        
        with open( file_path, 'wb' ) as f: f.write( EXAMPLE_FILE )
        with open( thumbnail_path, 'wb' ) as f: f.write( EXAMPLE_THUMBNAIL )
        
        local_booru_manager = HydrusGlobals.test_controller.GetManager( 'local_booru' )
        
        #
        
        self._test_local_booru_requests( connection, share_key, hashes[0], 404 )
        
        #
        
        info = {}
        info[ 'name' ] = 'name'
        info[ 'text' ] = 'text'
        info[ 'timeout' ] = 0
        info[ 'hashes' ] = hashes
        
        # hash, inbox, size, mime, width, height, duration, num_frames, num_words, tags_manager, locations_manager, ratings_manager
        
        media_results = [ ClientMedia.MediaResult( ( hash, True, 500, HC.IMAGE_JPEG, 640, 480, None, None, None, None, None, None ) ) for hash in hashes ]
        
        HydrusGlobals.test_controller.SetRead( 'local_booru_share_keys', [ share_key ] )
        HydrusGlobals.test_controller.SetRead( 'local_booru_share', info )
        HydrusGlobals.test_controller.SetRead( 'media_results', media_results )
        
        local_booru_manager.RefreshShares()
        
        #
        
        self._test_local_booru_requests( connection, share_key, hashes[0], 403 )
        
        #
        
        info[ 'timeout' ] = None
        HydrusGlobals.test_controller.SetRead( 'local_booru_share', info )
        
        local_booru_manager.RefreshShares()
        
        #
        
        self._test_local_booru_requests( connection, share_key, hashes[0], 200 )
        
        #
        
        HydrusGlobals.test_controller.SetRead( 'local_booru_share_keys', [] )
        
        local_booru_manager.RefreshShares()
        
        #
        
        self._test_local_booru_requests( connection, share_key, hashes[0], 404 )
        
    
    def _test_local_booru_requests( self, connection, share_key, hash, expected_result ):
        
        requests = []
        
        requests.append( '/gallery?share_key=' + share_key.encode( 'hex' ) )
        requests.append( '/page?share_key=' + share_key.encode( 'hex' ) + '&hash=' + hash.encode( 'hex' ) )
        requests.append( '/file?share_key=' + share_key.encode( 'hex' ) + '&hash=' + hash.encode( 'hex' ) )
        requests.append( '/thumbnail?share_key=' + share_key.encode( 'hex' ) + '&hash=' + hash.encode( 'hex' ) )
        
        for request in requests:
            
            connection.request( 'GET', request )
            
            response = connection.getresponse()
            
            data = response.read()
            
            self.assertEqual( response.status, expected_result )
            
        
    
    def _test_repo( self, service, host, port ):
        
        service_key = service.GetServiceKey()
        
        # news
        
        news = 'this is the news'
        
        service.Request( HC.POST, 'news', { 'news' : news } )
        
        written = HydrusGlobals.test_controller.GetWrite( 'news' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_news ) = args
        
        self.assertEqual( news, written_news )
        
        # num_petitions
        
        num_petitions = 23
        
        HydrusGlobals.test_controller.SetRead( 'num_petitions', num_petitions )
        
        response = service.Request( HC.GET, 'num_petitions' )
        
        self.assertEqual( response[ 'num_petitions' ], num_petitions )
        
        # petition
        
        action = HC.CONTENT_UPDATE_PETITION
        account_identifier = HydrusData.AccountIdentifier( account_key = HydrusData.GenerateKey() )
        reason = 'it sucks'
        contents = [ HydrusData.Content( HC.CONTENT_TYPE_FILES, [ HydrusData.GenerateKey() for i in range( 10 ) ] ) ]
        
        petition = HydrusData.ServerToClientPetition( action = action, petitioner_account_identifier = account_identifier, reason = reason, contents = contents )
        
        HydrusGlobals.test_controller.SetRead( 'petition', petition )
        
        response = service.Request( HC.GET, 'petition' )
        
        self.assertEqual( type( response ), HydrusData.ServerToClientPetition )
        
        # update
        
        begin = 100
        subindex_count = 5
        
        update = HydrusData.ServerToClientServiceUpdatePackage()
        update.SetBeginEnd( begin, begin + HC.UPDATE_DURATION - 1 )
        update.SetSubindexCount( subindex_count )
        
        path = ServerFiles.GetExpectedServiceUpdatePackagePath( service_key, begin )
        
        with open( path, 'wb' ) as f: f.write( update.DumpToNetworkString() )
        
        response = service.Request( HC.GET, 'service_update_package', { 'begin' : begin } )
        
        self.assertEqual( response.GetBegin(), update.GetBegin() )
        
        try: os.remove( path )
        except: pass
        
        subindex = 2
        num_hashes = 12
        tag = 'series:blah'
        hash_ids_to_hashes = { i : HydrusData.GenerateKey() for i in range( 12 ) }
        rows = [ ( tag, [ i for i in range( num_hashes ) ] ) ]
        
        update = HydrusData.ServerToClientContentUpdatePackage()
        update.AddContentData( HC.CONTENT_TYPE_MAPPINGS, HC.CONTENT_UPDATE_ADD, rows, hash_ids_to_hashes )
        
        path = ServerFiles.GetExpectedContentUpdatePackagePath( service_key, begin, subindex )
        
        with open( path, 'wb' ) as f: f.write( update.DumpToNetworkString() )
        
        response = service.Request( HC.GET, 'content_update_package', { 'begin' : begin, 'subindex' : subindex } )
        
        self.assertEqual( response.GetNumContentUpdates(), update.GetNumContentUpdates() )
        
        try: os.remove( path )
        except: pass
        
        update = HydrusData.ClientToServerContentUpdatePackage( {}, hash_ids_to_hashes )
        
        service.Request( HC.POST, 'content_update_package', { 'update' : update } )
        
        written = HydrusGlobals.test_controller.GetWrite( 'update' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_account, written_update ) = args
        
        self.assertEqual( update.GetHashes(), written_update.GetHashes() )
        
    
    def _test_restricted( self, service, host, port ):
        
        # access_key
        
        registration_key = HydrusData.GenerateKey()
        
        HydrusGlobals.test_controller.SetRead( 'access_key', self._access_key )
        
        request_headers = {}
        
        request_headers[ 'Hydrus-Key' ] = registration_key.encode( 'hex' )
        
        response = service.Request( HC.GET, 'access_key', request_headers = request_headers )
        
        self.assertEqual( response[ 'access_key' ], self._access_key )
        
        info = service.GetInfo()
        
        info[ 'access_key' ] = self._access_key
        
        # set up session
        
        last_error = 0
        
        account = self._account
        
        HydrusGlobals.test_controller.SetRead( 'service', service )
        
        HydrusGlobals.test_controller.SetRead( 'account_key_from_access_key', HydrusData.GenerateKey() )
        HydrusGlobals.test_controller.SetRead( 'account', self._account )
        
        # account
        
        response = service.Request( HC.GET, 'account' )
        
        self.assertEqual( repr( response[ 'account' ] ), repr( self._account ) )
        
        # account_info
        
        account_info = { 'message' : 'hello' }
        
        HydrusGlobals.test_controller.SetRead( 'account_info', account_info )
        HydrusGlobals.test_controller.SetRead( 'account_key_from_identifier', HydrusData.GenerateKey() )
        
        response = service.Request( HC.GET, 'account_info', { 'subject_account_key' : HydrusData.GenerateKey().encode( 'hex' ) } )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        response = service.Request( HC.GET, 'account_info', { 'subject_hash' : HydrusData.GenerateKey().encode( 'hex' ) } )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        response = service.Request( HC.GET, 'account_info', { 'subject_hash' : HydrusData.GenerateKey().encode( 'hex' ), 'subject_tag' : 'hello'.encode( 'hex' ) } )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        # account_types
        
        account_types = { 'message' : 'hello' }
        
        HydrusGlobals.test_controller.SetRead( 'account_types', account_types )
        
        response = service.Request( HC.GET, 'account_types' )
        
        self.assertEqual( response[ 'account_types' ], account_types )
        
        edit_log = 'blah'
        
        service.Request( HC.POST, 'account_types', { 'edit_log' : edit_log } )
        
        written = HydrusGlobals.test_controller.GetWrite( 'account_types' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_edit_log ) = args
        
        self.assertEqual( edit_log, written_edit_log )
        
        # registration_keys
        
        registration_key = HydrusData.GenerateKey()
        
        HydrusGlobals.test_controller.SetRead( 'registration_keys', [ registration_key ] )
        
        response = service.Request( HC.GET, 'registration_keys', { 'num' : 1, 'title' : 'blah' } )
        
        self.assertEqual( response[ 'registration_keys' ], [ registration_key ] )
        
        response = service.Request( HC.GET, 'registration_keys', { 'num' : 1, 'title' : 'blah', 'lifetime' : 100 } )
        
        self.assertEqual( response[ 'registration_keys' ], [ registration_key ] )
        
        # stats
        
        stats = { 'message' : 'hello' }
        
        HydrusGlobals.test_controller.SetRead( 'stats', stats )
        
        response = service.Request( HC.GET, 'stats' )
        
        self.assertEqual( response[ 'stats' ], stats )
        
    
    def _test_server_admin( self, service, host, port ):
        
        info = service.GetInfo()
        
        info[ 'host' ] = host
        info[ 'port' ] = port
        
        # init
        
        access_key = HydrusData.GenerateKey()
        
        HydrusGlobals.test_controller.SetRead( 'init', access_key )
        
        response = service.Request( HC.GET, 'init' )
        
        self.assertEqual( response[ 'access_key' ], access_key )
        
        #
        
        info[ 'access_key' ] = self._access_key
        
        # backup
        
        response = service.Request( HC.POST, 'backup' )
        
        # services
        
        services_info = { 'message' : 'hello' }
        
        HydrusGlobals.test_controller.SetRead( 'services_info', services_info )
        
        response = service.Request( HC.GET, 'services_info' )
        
        self.assertEqual( response[ 'services_info' ], services_info )
        
        edit_log = 'blah'
        
        registration_keys = service.Request( HC.POST, 'services', { 'edit_log' : edit_log } )
        
        written = HydrusGlobals.test_controller.GetWrite( 'services' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_key, written_edit_log ) = args
        
        self.assertEqual( edit_log, written_edit_log )
        
    
    def _test_tag_repo( self, service, host, port ):
        
        pass
        
    
    def test_local_service( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_LOCAL_FILE_PORT
        
        self._test_basics( host, port, https = False )
        self._test_local_file( host, port )
        
    
    def test_repository_file( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVICE_PORT
        
        info = self._file_service.GetInfo()
        
        info[ 'host' ] = host
        info[ 'port' ] = port
        
        self._test_basics( host, port )
        self._test_restricted( self._file_service, host, port )
        self._test_repo( self._file_service, host, port )
        self._test_file_repo( self._file_service, host, port )
        
    
    def test_repository_tag( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVICE_PORT + 1
        
        info = self._tag_service.GetInfo()
        
        info[ 'host' ] = host
        info[ 'port' ] = port
        
        self._test_basics( host, port )
        self._test_restricted( self._tag_service, host, port )
        self._test_repo( self._tag_service, host, port )
        self._test_tag_repo( self._tag_service, host, port )
        
    
    def test_server_admin( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVER_ADMIN_PORT
        
        info = self._admin_service.GetInfo()
        
        info[ 'host' ] = host
        info[ 'port' ] = port
        
        self._test_basics( host, port )
        self._test_restricted( self._admin_service, host, port )
        self._test_server_admin( self._admin_service, host, port )
        
    
    def test_local_booru( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_LOCAL_BOORU_PORT
        
        self._test_basics( host, port, https = False )
        self._test_local_booru( host, port )
        
    '''
class TestAMP( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        self._alice = HydrusData.GenerateKey()
        self._bob = HydrusData.GenerateKey()
        
        self._server_port = HC.DEFAULT_SERVICE_PORT + 10
        
        self._service_key = HydrusData.GenerateKey()
        
        def TWISTEDSetup():
            
            self._factory = HydrusServer.MessagingServiceFactory( self._service_key )
            
            reactor.listenTCP( self._server_port, self._factory )
            
        
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
