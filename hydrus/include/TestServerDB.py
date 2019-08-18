from . import ClientConstants as CC
from . import ClientData
from . import ClientDB
from . import ClientDefaults
from . import ClientDownloading
from . import ClientExporting
from . import ClientFiles
from . import ClientGUIManagement
from . import ClientGUIPages
from . import ClientImporting
from . import ClientImportLocal
from . import ClientImportOptions
from . import ClientImportFileSeeds
from . import ClientRatings
from . import ClientSearch
from . import ClientServices
from . import ClientTags
import collections
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusVideoHandling
from . import HydrusGlobals as HG
from . import HydrusNetwork
from . import HydrusSerialisable
import itertools
import os
from . import ServerDB
import shutil
import sqlite3
import stat
from . import TestController
import time
import threading
import unittest
import wx

class TestServerDB( unittest.TestCase ):
    
    def _read( self, action, *args, **kwargs ): return TestServerDB._db.Read( action, *args, **kwargs )
    def _write( self, action, *args, **kwargs ): return TestServerDB._db.Write( action, True, *args, **kwargs )
    
    @classmethod
    def setUpClass( cls ):
        
        cls._db = ServerDB.DB( HG.test_controller, TestController.DB_DIR, 'server' )
        
    
    @classmethod
    def tearDownClass( cls ):
        
        cls._db.Shutdown()
        
        while not cls._db.LoopIsFinished():
            
            time.sleep( 0.1 )
            
        
        del cls._db
        
    
    def _test_account_creation( self ):
        
        result = self._read( 'account_types', self._tag_service_key )
        
        ( service_admin_at, ) = result
        
        self.assertEqual( service_admin_at.GetTitle(), 'service admin' )
        self.assertEqual( service_admin_at.GetPermissions(), [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN ] )
        self.assertEqual( service_admin_at.GetMaxBytes(), None )
        self.assertEqual( service_admin_at.GetMaxRequests(), None )
        
        #
        
        user_at = HydrusData.AccountType( 'user', [ HC.GET_DATA, HC.POST_DATA ], ( 50000, 500 ) )
        
        edit_log = [ ( HC.ADD, user_at ) ]
        
        self._write( 'account_types', self._tag_service_key, edit_log )
        
        result = self._read( 'account_types', self._tag_service_key )
        
        ( at_1, at_2 ) = result
        
        d = { at_1.GetTitle() : at_1, at_2.GetTitle() : at_2 }
        
        at = d[ 'user' ]
        
        self.assertEqual( at.GetPermissions(), [ HC.GET_DATA, HC.POST_DATA ] )
        self.assertEqual( at.GetMaxBytes(), 50000 )
        self.assertEqual( at.GetMaxRequests(), 500 )
        
        #
        
        user_at_diff = HydrusData.AccountType( 'user different', [ HC.GET_DATA ], ( 40000, None ) )
        
        edit_log = [ ( HC.EDIT, ( 'user', user_at_diff ) ) ]
        
        self._write( 'account_types', self._tag_service_key, edit_log )
        
        result = self._read( 'account_types', self._tag_service_key )
        
        ( at_1, at_2 ) = result
        
        d = { at_1.GetTitle() : at_1, at_2.GetTitle() : at_2 }
        
        at = d[ 'user different' ]
        
        self.assertEqual( at.GetPermissions(), [ HC.GET_DATA ] )
        self.assertEqual( at.GetMaxBytes(), 40000 )
        self.assertEqual( at.GetMaxRequests(), None )
        
        #
        
        r_keys = self._read( 'registration_keys', self._tag_service_key, 5, 'user different', 86400 * 365 )
        
        self.assertEqual( len( r_keys ), 5 )
        
        for r_key in r_keys: self.assertEqual( len( r_key ), 32 )
        
        r_key = r_keys[0]
        
        access_key = self._read( 'access_key', self._tag_service_key, r_key )
        access_key_2 = self._read( 'access_key', self._tag_service_key, r_key )
        
        self.assertNotEqual( access_key, access_key_2 )
        
        self.assertRaises( HydrusExceptions.InsufficientCredentialsException, self._read, 'account_key_from_access_key', self._tag_service_key, access_key )
        
        account_key = self._read( 'account_key_from_access_key', self._tag_service_key, access_key_2 )
        
        self.assertRaises( HydrusExceptions.InsufficientCredentialsException, self._read, 'access_key', r_key )
        
    
    def _test_content_creation( self ):
        
        # create some tag and hashes business, try uploading a file, and test that
        
        # fetch content update, test it. I think that works
        
        pass
        
    
    def _test_init_server_admin( self ):
        
        result = self._read( 'access_key', HC.SERVER_ADMIN_KEY, b'init' )
        
        self.assertEqual( type( result ), bytes )
        self.assertEqual( len( result ), 32 )
        
        self._admin_access_key = result
        
        result = self._read( 'account_key_from_access_key', HC.SERVER_ADMIN_KEY, self._admin_access_key )
        
        self.assertEqual( type( result ), bytes )
        self.assertEqual( len( result ), 32 )
        
        self._admin_account_key = result
        
    
    def _test_service_creation( self ):
        
        self._tag_service_key = HydrusData.GenerateKey()
        self._file_service_key = HydrusData.GenerateKey()
        
        edit_log = []
        
        t_options = { 'max_monthly_data' : None, 'message' : 'tag repo message', 'port' : 100, 'upnp' : None }
        f_options = { 'max_monthly_data' : None, 'message' : 'file repo message', 'port' : 101, 'upnp' : None }
        
        edit_log.append( ( HC.ADD, ( self._tag_service_key, HC.TAG_REPOSITORY, t_options ) ) )
        edit_log.append( ( HC.ADD, ( self._file_service_key, HC.FILE_REPOSITORY, f_options ) ) )
        
        result = self._write( 'services', self._admin_account_key, edit_log )
        
        self.assertIn( self._tag_service_key, result )
        
        self._tag_service_admin_access_key = result[ self._tag_service_key ]
        
        self.assertEqual( type( self._tag_service_admin_access_key ), bytes )
        self.assertEqual( len( self._tag_service_admin_access_key ), 32 )
        
        self.assertIn( self._file_service_key, result )
        
        self._file_service_admin_access_key = result[ self._file_service_key ]
        
        self.assertEqual( type( self._tag_service_admin_access_key ), bytes )
        self.assertEqual( len( self._tag_service_admin_access_key ), 32 )
        
        #
        
        result = self._read( 'service_keys', HC.REPOSITORIES )
        
        self.assertEqual( set( result ), { self._tag_service_key, self._file_service_key } )
        
    
    def test_server( self ):
        
        self._test_init_server_admin()
        
        # broke since service rewrite
        #self._test_service_creation()
        
        #self._test_account_creation()
        
        #self._test_content_creation()
        

