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


class TestClientDB( unittest.TestCase ):
    
    @classmethod
    def setUpClass( self ):
        
        threading.Thread( target = reactor.run, kwargs = { 'installSignalHandlers' : 0 } ).start()
        
        services = []
        
        self._local_service_identifier = HC.ServerServiceIdentifier( 'local file', HC.LOCAL_FILE )
        self._file_service_identifier = HC.ServerServiceIdentifier( 'file service', HC.FILE_REPOSITORY )
        self._tag_service_identifier = HC.ServerServiceIdentifier( 'tag service', HC.TAG_REPOSITORY )
        
        self._access_key = os.urandom( 32 )
        self._file_hash = os.urandom( 32 )
        
        def TWISTEDSetup():
            
            reactor.listenTCP( HC.DEFAULT_SERVER_ADMIN_PORT, HydrusServer.HydrusServiceAdmin( HC.SERVER_ADMIN_IDENTIFIER, 'hello' ) )
            reactor.listenTCP( HC.DEFAULT_LOCAL_FILE_PORT, HydrusServer.HydrusServiceLocal( self._local_service_identifier, 'hello' ) )
            reactor.listenTCP( HC.DEFAULT_SERVICE_PORT, HydrusServer.HydrusServiceRepositoryFile( self._file_service_identifier, 'hello' ) )
            reactor.listenTCP( HC.DEFAULT_SERVICE_PORT + 1, HydrusServer.HydrusServiceLocal( self._tag_service_identifier, 'hello' ) )
            
        
        reactor.callFromThread( TWISTEDSetup )
        
        time.sleep( 1 )
        
        # set up (fake?) session manager, both client and server!
        
    
    @classmethod
    def tearDownClass( self ):
        
        reactor.callFromThread( reactor.stop )
        
    
    # might need to pass the s_i, in some of these, so I know what to prime the db with and test against
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
        
        os.remove( path )
        
        #
        
        path = CC.GetExpectedThumbnailPath( self._file_hash )
        
        with open( path, 'wb' ) as f: f.write( 'thumb' )
        
        connection.request( 'GET', '/thumbnail?hash=' + self._file_hash.encode( 'hex' ) )
        
        response = connection.getresponse()
        
        data = response.read()
        
        self.assertEqual( data, 'thumb' )
        
        os.remove( path )
        
    
    def _test_restricted( self, connection ):
        
        # add account_key to db, for registration
        
        # add account to db read
        # set up session, which should establish session for client
        # then fetch account
        
        pass
        
    
    def _test_server_admin( self, connection ):
        
        pass
        
    
    def _test_file_repo( self, connection ):
        
        pass
        
    
    def _test_tag_repo( self, connection ):
        
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
        
        file_connection = CC.ConnectionToService( HC.ClientServiceIdentifier( os.urandom( 32 ), HC.FILE_REPOSITORY, 'file repo' ), CC.Credentials( '127.0.0.1', HC.DEFAULT_SERVICE_PORT, access_key = self._access_key ) )
        
    
    def test_repository_tag( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVICE_PORT + 1
        
        self._test_basics( host, port )
        
        tag_connection = CC.ConnectionToService( HC.ClientServiceIdentifier( os.urandom( 32 ), HC.TAG_REPOSITORY, 'tag repo' ), CC.Credentials( '127.0.0.1', HC.DEFAULT_SERVICE_PORT + 1, access_key = self._access_key ) )
        
    
    def test_server_admin( self ):
        
        host = '127.0.0.1'
        port = HC.DEFAULT_SERVER_ADMIN_PORT
        
        self._test_basics( host, port )
        
        admin_connection = CC.ConnectionToService( HC.ClientServiceIdentifier( os.urandom( 32 ), HC.SERVER_ADMIN, 'server admin' ), CC.Credentials( '127.0.0.1', HC.DEFAULT_SERVER_ADMIN_PORT, access_key = self._access_key ) )
        
    
'''
root.putChild( '', HydrusServerResources.HydrusResourceWelcome( self._service_identifier, self._message ) )
root.putChild( 'favicon.ico', HydrusServerResources.hydrus_favicon )

root.putChild( 'file', HydrusServerResources.HydrusResourceCommandFileLocal( self._service_identifier ) )
root.putChild( 'thumbnail', HydrusServerResources.HydrusResourceCommandThumbnailLocal( self._service_identifier ) )

root.putChild( 'access_key', HydrusServerResources.HydrusResourceCommandAccessKey( self._service_identifier ) )
root.putChild( 'session_key', HydrusServerResources.HydrusResourceCommandSessionKey( self._service_identifier ) )

root.putChild( 'account', HydrusServerResources.HydrusResourceCommandRestrictedAccount( self._service_identifier ) )
root.putChild( 'account_info', HydrusServerResources.HydrusResourceCommandRestrictedAccountInfo( self._service_identifier ) )
root.putChild( 'account_types', HydrusServerResources.HydrusResourceCommandRestrictedAccountTypes( self._service_identifier ) )
root.putChild( 'registration_keys', HydrusServerResources.HydrusResourceCommandRestrictedRegistrationKeys( self._service_identifier ) )
root.putChild( 'stats', HydrusServerResources.HydrusResourceCommandRestrictedStats( self._service_identifier ) )

root.putChild( 'backup', HydrusServerResources.HydrusResourceCommandRestrictedBackup( self._service_identifier ) )
root.putChild( 'init', HydrusServerResources.HydrusResourceCommandInit( self._service_identifier ) )
root.putChild( 'services', HydrusServerResources.HydrusResourceCommandRestrictedServices( self._service_identifier ) )

root.putChild( 'news', HydrusServerResources.HydrusResourceCommandRestrictedNews( self._service_identifier ) )
root.putChild( 'num_petitions', HydrusServerResources.HydrusResourceCommandRestrictedNumPetitions( self._service_identifier ) )
root.putChild( 'petition', HydrusServerResources.HydrusResourceCommandRestrictedPetition( self._service_identifier ) )
root.putChild( 'update', HydrusServerResources.HydrusResourceCommandRestrictedUpdate( self._service_identifier ) )

root.putChild( 'file', HydrusServerResources.HydrusResourceCommandRestrictedFileRepository( self._service_identifier ) )
root.putChild( 'ip', HydrusServerResources.HydrusResourceCommandRestrictedIP( self._service_identifier ) )
root.putChild( 'thumbnail', HydrusServerResources.HydrusResourceCommandRestrictedThumbnailRepository( self._service_identifier ) )
'''