import ClientConstants as CC
import collections
import HydrusConstants as HC
import HydrusExceptions
import HydrusSessions
import os
import TestConstants
import unittest
import HydrusData
import HydrusGlobals
import wx

class TestSessions( unittest.TestCase ):
    
    def test_server( self ):
        
        discard = wx.GetApp().GetWrite( 'session' ) # just to discard gumph from testserver
        
        session_key_1 = os.urandom( 32 )
        service_key = os.urandom( 32 )
        
        permissions = [ HC.GET_DATA, HC.POST_DATA, HC.POST_PETITIONS, HC.RESOLVE_PETITIONS, HC.MANAGE_USERS, HC.GENERAL_ADMIN, HC.EDIT_SERVICES ]
        
        access_key = os.urandom( 32 )
        account_key = os.urandom( 32 )
        account_type = HydrusData.AccountType( 'account', permissions, ( None, None ) )
        created = HydrusData.GetNow() - 100000
        expires = HydrusData.GetNow() + 300
        used_bytes = 0
        used_requests = 0
        
        account = HydrusData.Account( account_key, account_type, created, expires, used_bytes, used_requests )
        
        expires = HydrusData.GetNow() - 10
        
        wx.GetApp().SetRead( 'sessions', [ ( session_key_1, service_key, account, expires ) ] )
        
        session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        with self.assertRaises( HydrusExceptions.SessionException ):
            
            session_manager.GetAccount( service_key, session_key_1 )
            
        
        # test fetching a session already in db, after bootup
        
        expires = HydrusData.GetNow() + 300
        
        wx.GetApp().SetRead( 'sessions', [ ( session_key_1, service_key, account, expires ) ] )
        
        session_manager = HydrusSessions.HydrusSessionManagerServer()
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, account )
        
        # test adding a session
        
        expires = HydrusData.GetNow() + 300
        
        account_key_2 = os.urandom( 32 )
        
        account_2 = HydrusData.Account( account_key_2, account_type, created, expires, used_bytes, used_requests )
        
        wx.GetApp().SetRead( 'account_key_from_access_key', account_key_2 )
        wx.GetApp().SetRead( 'account', account_2 )
        
        ( session_key_2, expires_2 ) = session_manager.AddSession( service_key, access_key )
        
        [ ( args, kwargs ) ] = wx.GetApp().GetWrite( 'session' )
        
        ( written_session_key, written_service_key, written_account_key, written_expires ) = args
        
        self.assertEqual( ( session_key_2, service_key, account_key_2, expires_2 ), ( written_session_key, written_service_key, written_account_key, written_expires ) )
        
        read_account = session_manager.GetAccount( service_key, session_key_2 )
        
        self.assertIs( read_account, account_2 )
        
        # test adding a new session for an account already in the manager
        
        wx.GetApp().SetRead( 'account_key_from_access_key', account_key )
        wx.GetApp().SetRead( 'account', account )
        
        ( session_key_3, expires_3 ) = session_manager.AddSession( service_key, access_key )
        
        [ ( args, kwargs ) ] = wx.GetApp().GetWrite( 'session' )
        
        ( written_session_key, written_service_key, written_account_key, written_expires ) = args
        
        self.assertEqual( ( session_key_3, service_key, account_key, expires_3 ), ( written_session_key, written_service_key, written_account_key, written_expires ) )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, account )
        
        read_account_original = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, read_account_original )
        
        # test individual account refresh
        
        expires = HydrusData.GetNow() + 300
        
        updated_account = HydrusData.Account( account_key, account_type, created, expires, 1, 1 )
        
        wx.GetApp().SetRead( 'account', updated_account )
        
        session_manager.RefreshAccounts( service_key, [ account_key ] )
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, updated_account )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, updated_account )
        
        # test all account refresh
        
        expires = HydrusData.GetNow() + 300
        
        updated_account_2 = HydrusData.Account( account_key, account_type, created, expires, 2, 2 )
        
        wx.GetApp().SetRead( 'sessions', [ ( session_key_1, service_key, updated_account_2, expires ), ( session_key_2, service_key, account_2, expires ), ( session_key_3, service_key, updated_account_2, expires ) ] )
        
        session_manager.RefreshAllAccounts()
        
        read_account = session_manager.GetAccount( service_key, session_key_1 )
        
        self.assertIs( read_account, updated_account_2 )
        
        read_account = session_manager.GetAccount( service_key, session_key_2 )
        
        self.assertIs( read_account, account_2 )
        
        read_account = session_manager.GetAccount( service_key, session_key_3 )
        
        self.assertIs( read_account, updated_account_2 )
        