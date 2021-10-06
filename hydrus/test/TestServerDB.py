import time
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core.networking import HydrusNetwork
from hydrus.core.networking import HydrusNetworking

from hydrus.server import ServerDB

from hydrus.test import TestController

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
        
        result = sorted( self._read( 'account_types', self._tag_service_key, self._tag_service_account ), key = lambda at: at.GetTitle() )
        
        ( self._tag_service_admin_account_type, self._null_account_type ) = result
        
        self.assertEqual( self._tag_service_admin_account_type.GetTitle(), 'administrator' )
        self.assertEqual( self._null_account_type.GetTitle(), 'null account' )
        
        #
        
        self._regular_user_account_type = HydrusNetwork.AccountType.GenerateNewAccountType( 'regular user', { HC.CONTENT_TYPE_MAPPINGS : HC.PERMISSION_ACTION_CREATE }, HydrusNetworking.BandwidthRules() )
        self._deletee_user_account_type = HydrusNetwork.AccountType.GenerateNewAccountType( 'deletee user', {}, HydrusNetworking.BandwidthRules() )
        
        new_account_types = [ self._tag_service_admin_account_type, self._null_account_type, self._regular_user_account_type, self._deletee_user_account_type ]
        
        #
        
        self._write( 'account_types', self._tag_service_key, self._tag_service_account, new_account_types, {} )
        
        edited_account_types = self._read( 'account_types', self._tag_service_key, self._tag_service_account )
        
        self.assertEqual(
            { at.GetAccountTypeKey() for at in edited_account_types },
            { at.GetAccountTypeKey() for at in ( self._tag_service_admin_account_type, self._null_account_type, self._regular_user_account_type, self._deletee_user_account_type ) }
        )
        
        #
        
        r_keys = self._read( 'registration_keys', self._tag_service_key, self._tag_service_account, 5, self._deletee_user_account_type.GetAccountTypeKey(), HydrusData.GetNow() + 86400 * 365 )
        
        access_keys = [ self._read( 'access_key', self._tag_service_key, r_key ) for r_key in r_keys ]
        
        account_keys = [ self._read( 'account_key_from_access_key', self._tag_service_key, access_key ) for access_key in access_keys ] 
        
        accounts = [ self._read( 'account', self._tag_service_key, account_key ) for account_key in account_keys ] 
        
        for account in accounts:
            
            self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._deletee_user_account_type.GetAccountTypeKey() )
            
        
        #
        
        deletee_account_type_keys_to_replacement_account_type_keys = { self._deletee_user_account_type.GetAccountTypeKey() : self._regular_user_account_type.GetAccountTypeKey() }
        
        new_account_types = [ self._tag_service_admin_account_type, self._null_account_type, self._regular_user_account_type ]
        
        self._write( 'account_types', self._tag_service_key, self._tag_service_account, new_account_types, deletee_account_type_keys_to_replacement_account_type_keys )
        
        accounts = [ self._read( 'account', self._tag_service_key, account_key ) for account_key in account_keys ] 
        
        self._tag_service_regular_account = accounts[0]
        
        for account in accounts:
            
            self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._regular_user_account_type.GetAccountTypeKey() )
            
        
        #
        
        r_keys = self._read( 'registration_keys', self._tag_service_key, self._tag_service_account, 5, self._regular_user_account_type.GetAccountTypeKey(), HydrusData.GetNow() + 86400 * 365 )
        
        self.assertEqual( len( r_keys ), 5 )
        
        for r_key in r_keys: self.assertEqual( len( r_key ), 32 )
        
        r_key = r_keys[0]
        
        access_key = self._read( 'access_key', self._tag_service_key, r_key )
        access_key_2 = self._read( 'access_key', self._tag_service_key, r_key )
        
        self.assertNotEqual( access_key, access_key_2 )
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            # this access key has been replaced
            self._read( 'account_key_from_access_key', self._tag_service_key, access_key )
            
        
        account_key = self._read( 'account_key_from_access_key', self._tag_service_key, access_key_2 )
        
        with self.assertRaises( HydrusExceptions.InsufficientCredentialsException ):
            
            # this registration token has been deleted
            self._read( 'access_key', self._tag_service_key, r_key )
            
        
    
    def _test_account_modification( self ):
        
        regular_account_key = self._tag_service_regular_account.GetAccountKey()
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._regular_user_account_type.GetAccountTypeKey() )
        
        self._write( 'modify_account_account_type', self._tag_service_key, self._tag_service_account, regular_account_key, self._tag_service_admin_account_type.GetAccountTypeKey() )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._tag_service_admin_account_type.GetAccountTypeKey() )
        
        self._write( 'modify_account_account_type', self._tag_service_key, self._tag_service_account, regular_account_key, self._regular_user_account_type.GetAccountTypeKey() )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertEqual( account.GetAccountType().GetAccountTypeKey(), self._regular_user_account_type.GetAccountTypeKey() )
        
        #
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertFalse( account.IsBanned() )
        
        ban_reason = 'oh no no no'
        
        self._write( 'modify_account_ban', self._tag_service_key, self._tag_service_account, regular_account_key, ban_reason, None )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertTrue( account.IsBanned() )
        
        ( reason, created, expires ) = account.GetBannedInfo()
        
        self.assertEqual( reason, ban_reason )
        self.assertTrue( HydrusData.GetNow() - 5 < created < HydrusData.GetNow() + 5 )
        self.assertEqual( expires, None )
        
        ban_reason = 'just having a giggle m8'
        ban_expires = HydrusData.GetNow() + 86400
        
        self._write( 'modify_account_ban', self._tag_service_key, self._tag_service_account, regular_account_key, ban_reason, ban_expires )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertTrue( account.IsBanned() )
        
        ( reason, created, expires ) = account.GetBannedInfo()
        
        self.assertEqual( reason, ban_reason )
        self.assertTrue( HydrusData.GetNow() - 5 < created < HydrusData.GetNow() + 5 )
        self.assertEqual( expires, ban_expires )
        
        self._write( 'modify_account_unban', self._tag_service_key, self._tag_service_account, regular_account_key )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertFalse( account.IsBanned() )
        
        #
        
        set_expires = HydrusData.GetNow() - 5
        
        self._write( 'modify_account_expires', self._tag_service_key, self._tag_service_account, regular_account_key, set_expires )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertTrue( account.IsExpired() )
        
        self.assertEqual( set_expires, account.GetExpires() )
        
        set_expires = HydrusData.GetNow() + 86400
        
        self._write( 'modify_account_expires', self._tag_service_key, self._tag_service_account, regular_account_key, set_expires )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertFalse( account.IsExpired() )
        
        self.assertEqual( set_expires, account.GetExpires() )
        
        set_expires = None
        
        self._write( 'modify_account_expires', self._tag_service_key, self._tag_service_account, regular_account_key, set_expires )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        self.assertFalse( account.IsExpired() )
        
        self.assertEqual( set_expires, account.GetExpires() )
        
        #
        
        set_message = 'hello'
        
        self._write( 'modify_account_set_message', self._tag_service_key, self._tag_service_account, regular_account_key, set_message )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        ( message, created ) = account.GetMessageAndTimestamp()
        
        self.assertEqual( message, set_message )
        
        set_message = ''
        
        self._write( 'modify_account_set_message', self._tag_service_key, self._tag_service_account, regular_account_key, set_message )
        
        account = self._read( 'account', self._tag_service_key, regular_account_key )
        
        ( message, created ) = account.GetMessageAndTimestamp()
        
        self.assertEqual( message, set_message )
        
    
    def _test_content_creation( self ):
        
        tag = 'character:samus aran'
        hash = HydrusData.GenerateKey()
        
        mappings_content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPINGS, ( tag, ( hash, ) ) )
        mapping_content = HydrusNetwork.Content( HC.CONTENT_TYPE_MAPPING, ( tag, hash ) )
        
        client_to_server_update = HydrusNetwork.ClientToServerUpdate()
        
        client_to_server_update.AddContent( HC.CONTENT_UPDATE_PEND, mappings_content )
        
        self._write( 'update', self._tag_service_key, self._tag_service_regular_account, client_to_server_update, HydrusData.GetNow() )
        
        # can extend this to generate and fetch an actual update given a timespan
        
        #
        
        result = self._read( 'account_from_content', self._tag_service_key, mapping_content )
        
        self.assertEqual( result.GetAccountKey(), self._tag_service_regular_account.GetAccountKey() )
        
    
    def _test_init_server_admin( self ):
        
        result = self._read( 'access_key', HC.SERVER_ADMIN_KEY, b'init' )
        
        self.assertEqual( type( result ), bytes )
        self.assertEqual( len( result ), 32 )
        
        self._admin_access_key = result
        
        #
        
        result = self._read( 'account_key_from_access_key', HC.SERVER_ADMIN_KEY, self._admin_access_key )
        
        self.assertEqual( type( result ), bytes )
        self.assertEqual( len( result ), 32 )
        
        self._admin_account_key = result
        
        #
        
        result = self._read( 'account', HC.SERVER_ADMIN_KEY, self._admin_account_key )
        
        self.assertEqual( type( result ), HydrusNetwork.Account )
        self.assertEqual( result.GetAccountKey(), self._admin_account_key )
        
        self._admin_account = result
        
    
    def _test_service_creation( self ):
        
        self._tag_service_key = HydrusData.GenerateKey()
        self._file_service_key = HydrusData.GenerateKey()
        
        current_services = self._read( 'services' )
        
        self._tag_service = HydrusNetwork.GenerateService( self._tag_service_key, HC.TAG_REPOSITORY, 'tag repo', 100 )
        self._file_service = HydrusNetwork.GenerateService( self._file_service_key, HC.FILE_REPOSITORY, 'file repo', 101 )
        
        new_services = list( current_services )
        new_services.append( self._tag_service )
        new_services.append( self._file_service )
        
        service_keys_to_access_keys = self._write( 'services', self._admin_account, new_services )
        
        self.assertEqual( set( service_keys_to_access_keys.keys() ), { self._tag_service_key, self._file_service_key } )
        
        self._tag_service_access_key = service_keys_to_access_keys[ self._tag_service_key ]
        self._file_service_access_key = service_keys_to_access_keys[ self._file_service_key ]
        
        self._tag_service_account_key = self._read( 'account_key_from_access_key', self._tag_service_key, self._tag_service_access_key )
        self._file_service_account_key = self._read( 'account_key_from_access_key', self._file_service_key, self._file_service_access_key )
        
        self._tag_service_account = self._read( 'account', self._tag_service_key, self._tag_service_account_key )
        self._file_service_account = self._read( 'account', self._file_service_key, self._file_service_account_key )
        
        self.assertEqual( self._tag_service_account.GetAccountKey(), self._tag_service_account_key )
        self.assertEqual( self._file_service_account.GetAccountKey(), self._file_service_account_key )
        
    
    def test_server( self ):
        
        self._test_init_server_admin()
        
        self._test_service_creation()
        
        self._test_account_creation()
        
        self._test_content_creation()
        
        self._test_account_modification()
        

