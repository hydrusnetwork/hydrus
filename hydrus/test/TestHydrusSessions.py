import hashlib
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusSessions
from hydrus.core import HydrusTime
from hydrus.core.networking import HydrusNetwork

class TestSessions( unittest.TestCase ):
    
    def test_server( self ):
        
        discard = HG.test_controller.GetWrite( 'session' ) # just to discard gumph from testserver
        
        session_key_1 = HydrusData.GenerateKey()
        service_key = HydrusData.GenerateKey()
        
        permissions = [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ]
        
        account_type = HydrusNetwork.AccountType.GenerateAdminAccountType( HC.SERVER_ADMIN )
        created = HydrusTime.GetNow() - 100000
        expires = HydrusTime.GetNow() + 300
        
        account_key_1 = HydrusData.GenerateKey()
        account_key_2 = HydrusData.GenerateKey()
        
        access_key_1 = HydrusData.GenerateKey()
        hashed_access_key_1 = hashlib.sha256( access_key_1 ).digest()
        
        access_key_2 = HydrusData.GenerateKey()
        hashed_access_key_2 = hashlib.sha256( access_key_2 ).digest()
        
        account = HydrusNetwork.Account( account_key_1, account_type, created, expires )
        account_2 = HydrusNetwork.Account( account_key_2, account_type, created, expires )
        
        # test timeout
        
        expires = HydrusTime.GetNow() - 10
        
        HG.test_controller.SetRead( 'sessions', [ ( session_key_1, service_key, account, hashed_access_key_1, expires ) ] )
        
        session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        with self.assertRaises( HydrusExceptions.SessionException ):
            
            session_manager.GetAccount( service_key, session_key_1 )
            
        
        # test missing
        
        with self.assertRaises( HydrusExceptions.SessionException ):
            
            session_manager.GetAccount( service_key, HydrusData.GenerateKey() )
            
        
        # test fetching a session already in db, after bootup
        
        expires = HydrusTime.GetNow() + 300
        
        HG.test_controller.SetRead( 'sessions', [ ( session_key_1, service_key, account, hashed_access_key_1, expires ) ] )
        
        session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, account )
        
        read_account = session_manager.GetAccountFromAccessKey( service_key, access_key_1 )
        
        self.assertIs( read_account, account )
        
        # test too busy to add a new session for a new account it doesn't know about
        
        HG.server_busy.acquire()
        
        with self.assertRaises( HydrusExceptions.ServerBusyException ):
            
            session_manager.AddSession( service_key, HydrusData.GenerateKey() )
            
            session_manager.GetAccountFromAccessKey( service_key, HydrusData.GenerateKey() )
            
        
        # but ok to get for a session that already exists while busy
        
        session_manager.GetAccount( service_key, session_key_1 )
        session_manager.GetAccountFromAccessKey( service_key, access_key_1 )
        
        HG.server_busy.release()
        
        # test adding a session
        
        HG.test_controller.ClearWrites( 'session' )
        
        expires = HydrusTime.GetNow() + 300
        
        HG.test_controller.SetRead( 'account_key_from_access_key', account_key_2 )
        HG.test_controller.SetRead( 'account', account_2 )
        
        ( session_key_2, expires_2 ) = session_manager.AddSession( service_key, access_key_2 )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetWrite( 'session' )
        
        ( written_session_key, written_service_key, written_account_key, written_expires ) = args
        
        self.assertEqual( ( session_key_2, service_key, account_key_2, expires_2 ), ( written_session_key, written_service_key, written_account_key, written_expires ) )
        
        read_account = session_manager.GetAccount( service_key, session_key_2 )
        
        self.assertIs( read_account, account_2 )
        
        read_account = session_manager.GetAccountFromAccessKey( service_key, access_key_2 )
        
        self.assertIs( read_account, account_2 )
        
        # test adding a new session for an account already in the manager
        
        HG.test_controller.SetRead( 'account_key_from_access_key', account_key_1 )
        HG.test_controller.SetRead( 'account', account )
        
        ( session_key_3, expires_3 ) = session_manager.AddSession( service_key, access_key_1 )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetWrite( 'session' )
        
        ( written_session_key, written_service_key, written_account_key, written_expires ) = args
        
        self.assertEqual( ( session_key_3, service_key, account_key_1, expires_3 ), ( written_session_key, written_service_key, written_account_key, written_expires ) )
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, account )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, account )
        
        read_account = session_manager.GetAccountFromAccessKey( service_key, access_key_1 )
        
        self.assertIs( read_account, account )
        
        # test individual account refresh
        
        expires = HydrusTime.GetNow() + 300
        
        new_obj_account_1 = HydrusNetwork.Account( account_key_1, account_type, created, expires )
        
        HG.test_controller.SetRead( 'account', new_obj_account_1 )
        
        session_manager.RefreshAccounts( service_key, [ account_key_1 ] )
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, new_obj_account_1 )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, new_obj_account_1 )
        
        read_account = session_manager.GetAccountFromAccessKey( service_key, access_key_1 )
        
        self.assertIs( read_account, new_obj_account_1 )
        
        # test all account refresh
        
        expires = HydrusTime.GetNow() + 300
        
        new_obj_account_2 = HydrusNetwork.Account( account_key_2, account_type, created, expires )
        
        HG.test_controller.SetRead( 'sessions', [ ( session_key_1, service_key, new_obj_account_2, hashed_access_key_2, expires ), ( session_key_2, service_key, new_obj_account_1, hashed_access_key_1, expires ), ( session_key_3, service_key, new_obj_account_2, hashed_access_key_2, expires ) ] )
        
        session_manager.RefreshAllAccounts()
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, new_obj_account_2 )
        
        read_account = session_manager.GetAccount( service_key, session_key_2 )
        
        self.assertIs( read_account, new_obj_account_1 )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, new_obj_account_2 )
        
        read_account = session_manager.GetAccountFromAccessKey( service_key, access_key_1 )
        
        self.assertIs( read_account, new_obj_account_1 )
        
        read_account = session_manager.GetAccountFromAccessKey( service_key, access_key_2 )
        
        self.assertIs( read_account, new_obj_account_2 )
        
