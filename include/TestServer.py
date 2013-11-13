import ClientConstants as CC
import httplib
import HydrusConstants as HC
import HydrusServer
import HydrusServerResources
import itertools
import os
import ServerConstants as SC
import shutil
import stat
import TestConstants
import time
import threading
import unittest
from twisted.internet import reactor

class TestServer( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
        
        services = []
        
        self._local_service_identifier = HC.ServerServiceIdentifier( 'local file', HC.LOCAL_FILE )
        self._file_service_identifier = HC.ServerServiceIdentifier( 'file service', HC.FILE_REPOSITORY )
        self._tag_service_identifier = HC.ServerServiceIdentifier( 'tag service', HC.TAG_REPOSITORY )
        
        permissions = [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ]
        
        account_id = 1
        account_type = HC.AccountType( 'account', permissions, ( None, None ) )
        created = HC.GetNow() - 100000
        expires = None
        used_data = ( 0, 0 )
        
        self._account = HC.Account( account_id, account_type, created, expires, used_data )
        
        self._access_key = os.urandom( 32 )
        self._file_hash = os.urandom( 32 )
        
        def TWISTEDSetup():
            
            reactor.listenTCP( HC.DEFAULT_SERVER_ADMIN_PORT, HydrusServer.HydrusServiceAdmin( HC.SERVER_ADMIN_IDENTIFIER, 'hello' ) )
            reactor.listenTCP( HC.DEFAULT_LOCAL_FILE_PORT, HydrusServer.HydrusServiceLocal( self._local_service_identifier, 'hello' ) )
            reactor.listenTCP( HC.DEFAULT_SERVICE_PORT, HydrusServer.HydrusServiceRepositoryFile( self._file_service_identifier, 'hello' ) )
            reactor.listenTCP( HC.DEFAULT_SERVICE_PORT + 1, HydrusServer.HydrusServiceRepositoryTag( self._tag_service_identifier, 'hello' ) )
            
        
        reactor.callFromThread( TWISTEDSetup )
        
        time.sleep( 1 )
        
    
    @classmethod
    def tearDownClass( self ):
        
        reactor.callFromThread( reactor.stop )
        
    
    def _test_basics( self, host, port ):
        
        connection = httplib.HTTPConnection( host, port, timeout = 10 )
        
        #
        
        connection.request( 'GET', '/' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        p1 = data == HydrusServerResources.CLIENT_ROOT_MESSAGE
        p2 = data == HydrusServerResources.ROOT_MESSAGE_BEGIN + 'hello' + HydrusServerResources.ROOT_MESSAGE_END
        
        self.assertTrue( p1 or p2 )
        
        #
        
        with open( HC.STATIC_DIR + os.path.sep + 'hydrus.ico', 'rb' ) as f: favicon = f.read()
        
        connection.request( 'GET', '/favicon.ico' )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, favicon )
        
    
    def _test_local_file( self, host, port ):
        
        connection = httplib.HTTPConnection( host, port, timeout = 10 )
        
        #
        
        path = CC.GetExpectedFilePath( self._file_hash, HC.IMAGE_JPEG )
        
        with open( path, 'wb' ) as f: f.write( 'file' )
        
        connection.request( 'GET', '/file?hash=' + self._file_hash.encode( 'hex' ) )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, 'file' )
        
        try: os.remove( path )
        except: pass
        
        #
        
        path = CC.GetExpectedThumbnailPath( self._file_hash )
        
        with open( path, 'wb' ) as f: f.write( 'thumb' )
        
        connection.request( 'GET', '/thumbnail?hash=' + self._file_hash.encode( 'hex' ) )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, 'thumb' )
        
        try: os.remove( path )
        except: pass
        
    
    def _test_file_repo( self, host, port ):
        
        # set up connection
        
        service_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.FILE_REPOSITORY, 'service' )
        
        credentials = CC.Credentials( host, port, self._access_key )
        
        connection = CC.ConnectionToService( service_identifier, credentials )
        
        file_connection = httplib.HTTPConnection( host, port, timeout = 10 )
        
        # file
        
        path = SC.GetExpectedPath( 'file', self._file_hash )
        
        with open( path, 'wb' ) as f: f.write( 'file' )
        
        response = connection.Get( 'file', hash = self._file_hash.encode( 'hex' ) )
        
        self.assertEqual( response, 'file' )
        
        try: os.remove( path )
        except: pass
        
        path = HC.STATIC_DIR + os.path.sep + 'hydrus.png'

        with open( path, 'rb' ) as f: file = f.read()
        
        connection.Post( 'file', file = file )
        
        written = HC.app.GetWrite( 'file' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_identifier, written_account, written_file_dict ) = args
        
        self.assertEqual( written_file_dict[ 'hash' ], '\xadm5\x99\xa6\xc4\x89\xa5u\xeb\x19\xc0&\xfa\xce\x97\xa9\xcdey\xe7G(\xb0\xce\x94\xa6\x01\xd22\xf3\xc3' )
        self.assertEqual( written_file_dict[ 'ip' ], '127.0.0.1' )
        self.assertEqual( written_file_dict[ 'height' ], 200 )
        self.assertEqual( written_file_dict[ 'width' ], 200 )
        self.assertEqual( written_file_dict[ 'mime' ], 2 )
        self.assertEqual( written_file_dict[ 'size' ], 5270 )
        
        # ip
        
        ( ip, timestamp ) = ( '94.45.87.123', HC.GetNow() - 100000 )
        
        HC.app.SetRead( 'ip', ( ip, timestamp ) )
        
        response = connection.Get( 'ip', hash = self._file_hash.encode( 'hex' ) )
        
        self.assertEqual( response[ 'ip' ], ip )
        self.assertEqual( response[ 'timestamp' ], timestamp )
        
        # thumbnail
        
        path = SC.GetExpectedPath( 'thumbnail', self._file_hash )
        
        with open( path, 'wb' ) as f: f.write( 'thumb' )
        
        response = connection.Get( 'thumbnail', hash = self._file_hash.encode( 'hex' ) )
        
        self.assertEqual( response, 'thumb' )
        
        try: os.remove( path )
        except: pass
        
    
    def _test_repo( self, host, port, service_type ):
        
        # set up connection
        
        service_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), service_type, 'service' )
        
        credentials = CC.Credentials( host, port, self._access_key )
        
        connection = CC.ConnectionToService( service_identifier, credentials )
        
        # news
        
        news = 'this is the news'
        
        connection.Post( 'news', news = news )
        
        written = HC.app.GetWrite( 'news' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_identifier, written_news ) = args
        
        self.assertEqual( news, written_news )
        
        # num_petitions
        
        num_petitions = 23
        
        HC.app.SetRead( 'num_petitions', num_petitions )
        
        response = connection.Get( 'num_petitions' )
        
        self.assertEqual( response[ 'num_petitions' ], num_petitions )
        
        # petition
        
        petition = 'petition'
        
        HC.app.SetRead( 'petition', petition )
        
        response = connection.Get( 'petition' )
        
        self.assertEqual( response[ 'petition' ], petition )
        
        # update
        
        update = 'update'
        
        update_key = os.urandom( 32 )
        
        path = SC.GetExpectedPath( 'update', update_key )
        
        with open( path, 'wb' ) as f: f.write( update )
        
        HC.app.SetRead( 'update_key', update_key )
        
        response = connection.Get( 'update', begin = 100 )
        
        self.assertEqual( response, update )
        
        try: os.remove( path )
        except: pass
        
        connection.Post( 'update', update = update )
        
        written = HC.app.GetWrite( 'update' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_identifier, written_account, written_update ) = args
        
        self.assertEqual( update, written_update )
        
    
    def _test_restricted( self, host, port, service_type ):
        
        # access_key
        
        registration_key = os.urandom( 32 )
        
        HC.app.SetRead( 'access_key', self._access_key )
        
        connection = HC.get_connection( host = host, port = port )
        
        headers = {}
        
        headers[ 'Hydrus-Key' ] = registration_key.encode( 'hex' )
        
        response = connection.request( 'GET', '/access_key', headers = headers )
        
        self.assertEqual( response[ 'access_key' ], self._access_key )
        
        # set up connection
        
        service_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), service_type, 'service' )
        
        credentials = CC.Credentials( host, port, self._access_key )
        
        connection = CC.ConnectionToService( service_identifier, credentials )
        
        # set up session
        
        last_error = 0
        
        account = self._account
        
        service_for_session_manager = CC.ServiceRemoteRestricted( service_identifier, credentials, last_error, account )
        
        HC.app.SetRead( 'service', service_for_session_manager )
        
        HC.app.SetRead( 'account', self._account )
        
        # account
        
        response = connection.Get( 'account' )
        
        self.assertEqual( repr( response[ 'account' ] ), repr( self._account ) )
        
        # account_info
        
        account_info = { 'message' : 'hello' }
        
        HC.app.SetRead( 'account_info', account_info )
        
        response = connection.Get( 'account_info', subject_account_id = 1 )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        response = connection.Get( 'account_info', subject_access_key = os.urandom( 32 ).encode( 'hex' ) )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        response = connection.Get( 'account_info', subject_hash = os.urandom( 32 ).encode( 'hex' ) )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        response = connection.Get( 'account_info', subject_hash = os.urandom( 32 ).encode( 'hex' ), subject_tag = 'hello'.encode( 'hex' ) )
        
        self.assertEqual( response[ 'account_info' ], account_info )
        
        # account_types
        
        account_types = { 'message' : 'hello' }
        
        HC.app.SetRead( 'account_types', account_types )
        
        response = connection.Get( 'account_types' )
        
        self.assertEqual( response[ 'account_types' ], account_types )
        
        edit_log = 'blah'
        
        connection.Post( 'account_types', edit_log = edit_log )
        
        written = HC.app.GetWrite( 'account_types' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_identifier, written_edit_log ) = args
        
        self.assertEqual( edit_log, written_edit_log )
        
        # registration_keys
        
        registration_key = os.urandom( 32 )
        
        HC.app.SetRead( 'registration_keys', [ registration_key ] )
        
        response = connection.Get( 'registration_keys', num = 1, title = 'blah' )
        
        self.assertEqual( response[ 'registration_keys' ], [ registration_key ] )
        
        response = connection.Get( 'registration_keys', num = 1, title = 'blah', expiration = 100 )
        
        self.assertEqual( response[ 'registration_keys' ], [ registration_key ] )
        
        # stats
        
        stats = { 'message' : 'hello' }
        
        HC.app.SetRead( 'stats', stats )
        
        response = connection.Get( 'stats' )
        
        self.assertEqual( response[ 'stats' ], stats )
        
    
    def _test_server_admin( self, host, port ):
        
        # set up init connection 
        service_identifier = HC.ClientServiceIdentifier( os.urandom( 32 ), HC.SERVER_ADMIN, 'server admin' )
        
        credentials = CC.Credentials( host, port )
        
        connection = CC.ConnectionToService( service_identifier, credentials )
        
        # init
        
        access_key = os.urandom( 32 )
        
        HC.app.SetRead( 'init', access_key )
        
        response = connection.Get( 'init' )
        
        self.assertEqual( response[ 'access_key' ], access_key )
        
        # set up connection
        
        credentials = CC.Credentials( host, port, self._access_key )
        
        connection = CC.ConnectionToService( service_identifier, credentials )
        
        # backup
        
        response = connection.Post( 'backup' )
        
        # services
        
        services = { 'message' : 'hello' }
        
        HC.app.SetRead( 'services', services )
        
        response = connection.Get( 'services' )
        
        self.assertEqual( response[ 'services_info' ], services )
        
        edit_log = 'blah'
        
        connection.Post( 'services', edit_log = edit_log )
        
        written = HC.app.GetWrite( 'services' )
        
        [ ( args, kwargs ) ] = written
        
        ( written_service_identifier, written_edit_log ) = args
        
        self.assertEqual( edit_log, written_edit_log )
        
    
    def _test_tag_repo( self, host, port ):
        
        pass
        
    
    def test_local_service( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_LOCAL_FILE_PORT
        
        self._test_basics( host, port )
        self._test_local_file( host, port )
        
    
    def test_repository_file( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVICE_PORT
        
        self._test_basics( host, port )
        self._test_restricted( host, port, HC.FILE_REPOSITORY )
        self._test_repo( host, port, HC.FILE_REPOSITORY )
        self._test_file_repo( host, port )
        
    
    def test_repository_tag( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVICE_PORT + 1
        
        self._test_basics( host, port )
        self._test_restricted( host, port, HC.TAG_REPOSITORY )
        self._test_repo( host, port, HC.TAG_REPOSITORY )
        self._test_tag_repo( host, port )
        
    
    def test_server_admin( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVER_ADMIN_PORT
        
        self._test_basics( host, port )
        self._test_restricted( host, port, HC.SERVER_ADMIN )
        self._test_server_admin( host, port )
        
    