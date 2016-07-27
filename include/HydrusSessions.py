import collections
import hashlib
import httplib
import HydrusConstants as HC
import HydrusExceptions
import os
import Queue
import re
import sqlite3
import sys
import threading
import time
import traceback
import urllib
import yaml
from twisted.internet.threads import deferToThread
import HydrusData
import HydrusGlobals

HYDRUS_SESSION_LIFETIME = 30 * 86400
'''
class HydrusMessagingSessionManagerServer( object ):
    
    def __init__( self ):
        
        existing_sessions = HydrusGlobals.controller.Read( 'messaging_sessions' )
        
        self._service_keys_to_sessions = collections.defaultdict( dict )
        
        for ( service_key, session_tuples ) in existing_sessions:
            
            self._service_keys_to_sessions[ service_key ] = { session_key : ( account, name, expires ) for ( session_key, account, name, expires ) in session_tuples }
            
        
        self._lock = threading.Lock()
        
    
    def GetIdentityAndName( self, service_key, session_key ):
        
        with self._lock:
            
            if session_key not in self._service_keys_to_sessions[ service_key ]: raise HydrusExceptions.SessionException( 'Did not find that session!' )
            else:
                
                ( account, name, expires ) = self._service_keys_to_sessions[ service_key ][ session_key ]
                
                if HydrusData.TimeHasPassed( expires ):
                    
                    del self._service_keys_to_sessions[ service_key ][ session_key ]
                    
                    raise HydrusExceptions.SessionException( 'Session expired! Try again!' )
                    
                
                return ( account.GetAccountKey(), name )
                
            
        
    
    def AddSession( self, service_key, access_key, name ):
        
        session_key = HydrusData.GenerateKey()
        
        account_key = HydrusGlobals.controller.Read( 'account_key_from_access_key', service_key, access_key )
        
        account = HydrusGlobals.controller.Read( 'account', service_key, account_key )
        
        now = HydrusData.GetNow()
        
        expires = now + HYDRUS_SESSION_LIFETIME
        
        with self._lock: self._service_keys_to_sessions[ service_key ][ session_key ] = ( account, name, expires )
        
        HydrusGlobals.controller.Write( 'messaging_session', service_key, session_key, account_key, name, expires )
        
        return session_key
        
    '''
class HydrusSessionManagerServer( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self.RefreshAllAccounts()
        
        HydrusGlobals.controller.sub( self, 'RefreshAllAccounts', 'update_all_session_accounts' )
        
    
    def AddSession( self, service_key, access_key ):
        
        with self._lock:
            
            account_key = HydrusGlobals.controller.Read( 'account_key_from_access_key', service_key, access_key )
            
            account_keys_to_accounts = self._service_keys_to_account_keys_to_accounts[ service_key ]
            
            if account_key not in account_keys_to_accounts:
                
                account = HydrusGlobals.controller.Read( 'account', account_key )
                
                account_keys_to_accounts[ account_key ] = account
                
            
            session_key = HydrusData.GenerateKey()
            
            now = HydrusData.GetNow()
            
            expires = now + HYDRUS_SESSION_LIFETIME
            
            HydrusGlobals.controller.Write( 'session', session_key, service_key, account_key, expires )
            
            self._service_keys_to_session_keys_to_sessions[ service_key ][ session_key ] = ( account_key, expires )
            
        
        return ( session_key, expires )
        
    
    def GetAccount( self, service_key, session_key ):
        
        with self._lock:
            
            session_keys_to_sessions = self._service_keys_to_session_keys_to_sessions[ service_key ]
            
            if session_key in session_keys_to_sessions:
                
                ( account_key, expires ) = session_keys_to_sessions[ session_key ]
                
                if HydrusData.TimeHasPassed( expires ):
                    
                    del session_keys_to_sessions[ session_key ]
                    
                else:
                    
                    account = self._service_keys_to_account_keys_to_accounts[ service_key ][ account_key ]
                    
                    return account
                    
                
            
            raise HydrusExceptions.SessionException( 'Did not find that session! Try again!' )
            
        
    
    def RefreshAccounts( self, service_key, account_keys = None ):
        
        with self._lock:
            
            account_keys_to_accounts = self._service_keys_to_account_keys_to_accounts[ service_key ]
            
            if account_keys is None:
                
                account_keys = account_keys_to_accounts.keys()
                
            
            for account_key in account_keys:
                
                account = HydrusGlobals.controller.Read( 'account', account_key )
                
                account_keys_to_accounts[ account_key ] = account
                
            
        
    
    def RefreshAllAccounts( self ):
        
        with self._lock:
            
            self._service_keys_to_session_keys_to_sessions = collections.defaultdict( dict )
            
            self._service_keys_to_account_keys_to_accounts = collections.defaultdict( dict )
            
            #
            
            existing_sessions = HydrusGlobals.controller.Read( 'sessions' )
            
            for ( session_key, service_key, account, expires ) in existing_sessions:
                
                account_key = account.GetAccountKey()
                
                self._service_keys_to_session_keys_to_sessions[ service_key ][ session_key ] = ( account_key, expires )
                
                self._service_keys_to_account_keys_to_accounts[ service_key ][ account_key ] = account
                
            
        
    