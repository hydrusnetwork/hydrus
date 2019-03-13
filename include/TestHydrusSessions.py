from . import ClientConstants as CC
import collections
from . import HydrusConstants as HC
from . import HydrusExceptions
from . import HydrusNetwork
from . import HydrusSessions
import os
import unittest
from . import HydrusData
from . import HydrusGlobals as HG

class TestSessions( unittest.TestCase ):
    
    def test_server( self ):
        
        discard = HG.test_controller.GetWrite( 'session' ) # just to discard gumph from testserver
        
        session_key_1 = HydrusData.GenerateKey()
        service_key = HydrusData.GenerateKey()
        
        permissions = [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ]
        
        access_key = HydrusData.GenerateKey()
        account_key = HydrusData.GenerateKey()
        account_type = HydrusNetwork.AccountType.GenerateAdminAccountType( HC.SERVER_ADMIN )
        created = HydrusData.GetNow() - 100000
        expires = HydrusData.GetNow() + 300
        
        account = HydrusNetwork.Account( account_key, account_type, created, expires )
        
        expires = HydrusData.GetNow() - 10
        
        HG.test_controller.SetRead( 'sessions', [ ( session_key_1, service_key, account, expires ) ] )
        
        session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        with self.assertRaises( HydrusExceptions.SessionException ):
            
            session_manager.GetAccount( service_key, session_key_1 )
            
        
        # test fetching a session already in db, after bootup
        
        expires = HydrusData.GetNow() + 300
        
        HG.test_controller.SetRead( 'sessions', [ ( session_key_1, service_key, account, expires ) ] )
        
        session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, account )
        
        # test adding a session
        
        HG.test_controller.ClearWrites( 'session' )
        
        expires = HydrusData.GetNow() + 300
        
        account_key_2 = HydrusData.GenerateKey()
        
        account_2 = HydrusNetwork.Account( account_key_2, account_type, created, expires )
        
        HG.test_controller.SetRead( 'account_key_from_access_key', account_key_2 )
        HG.test_controller.SetRead( 'account', account_2 )
        
        ( session_key_2, expires_2 ) = session_manager.AddSession( service_key, access_key )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetWrite( 'session' )
        
        ( written_session_key, written_service_key, written_account_key, written_expires ) = args
        
        self.assertEqual( ( session_key_2, service_key, account_key_2, expires_2 ), ( written_session_key, written_service_key, written_account_key, written_expires ) )
        
        read_account = session_manager.GetAccount( service_key, session_key_2 )
        
        self.assertIs( read_account, account_2 )
        
        # test adding a new session for an account already in the manager
        
        HG.test_controller.SetRead( 'account_key_from_access_key', account_key )
        HG.test_controller.SetRead( 'account', account )
        
        ( session_key_3, expires_3 ) = session_manager.AddSession( service_key, access_key )
        
        [ ( args, kwargs ) ] = HG.test_controller.GetWrite( 'session' )
        
        ( written_session_key, written_service_key, written_account_key, written_expires ) = args
        
        self.assertEqual( ( session_key_3, service_key, account_key, expires_3 ), ( written_session_key, written_service_key, written_account_key, written_expires ) )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, account )
        
        read_account_original = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, read_account_original )
        
        # test individual account refresh
        
        expires = HydrusData.GetNow() + 300
        
        updated_account = HydrusNetwork.Account( account_key, account_type, created, expires )
        
        HG.test_controller.SetRead( 'account', updated_account )
        
        session_manager.RefreshAccounts( service_key, [ account_key ] )
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, updated_account )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, updated_account )
        
        # test all account refresh
        
        expires = HydrusData.GetNow() + 300
        
        updated_account_2 = HydrusNetwork.Account( account_key, account_type, created, expires )
        
        HG.test_controller.SetRead( 'sessions', [ ( session_key_1, service_key, updated_account_2, expires ), ( session_key_2, service_key, account_2, expires ), ( session_key_3, service_key, updated_account_2, expires ) ] )
        
        session_manager.RefreshAllAccounts()
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, updated_account_2 )
        
        read_account = session_manager.GetAccount( service_key, session_key_2 )
        
        self.assertIs( read_account, account_2 )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, updated_account_2 )
        
