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
        
    
class HydrusSessionManagerClient( object ):
    
    def __init__( self ):
        
        existing_sessions = HydrusGlobals.controller.Read( 'hydrus_sessions' )
        
        self._service_keys_to_sessions = { service_key : ( session_key, expires ) for ( service_key, session_key, expires ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def DeleteSessionKey( self, service_key ):
        
        with self._lock:
            
            HydrusGlobals.controller.Write( 'delete_hydrus_session_key', service_key )
            
            if service_key in self._service_keys_to_sessions: del self._service_keys_to_sessions[ service_key ]
            
        
    
    def GetSessionKey( self, service_key ):
        
        now = HydrusData.GetNow()
        
        with self._lock:
            
            if service_key in self._service_keys_to_sessions:
                
                ( session_key, expires ) = self._service_keys_to_sessions[ service_key ]
                
                if now + 600 > expires: del self._service_keys_to_sessions[ service_key ]
                else: return session_key
                
            
            # session key expired or not found
            
            service = HydrusGlobals.controller.GetServicesManager().GetService( service_key )
            
            ( response_gumpf, cookies ) = service.Request( HC.GET, 'session_key', return_cookies = True )
            
            try: session_key = cookies[ 'session_key' ].decode( 'hex' )
            except: raise Exception( 'Service did not return a session key!' )
            
            expires = now + HYDRUS_SESSION_LIFETIME
            
            self._service_keys_to_sessions[ service_key ] = ( session_key, expires )
            
            HydrusGlobals.controller.Write( 'hydrus_session', service_key, session_key, expires )
            
            return session_key
            
        
    
class HydrusSessionManagerServer( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self.RefreshAllAccounts()
        
        HydrusGlobals.controller.sub( self, 'RefreshAllAccounts', 'update_all_session_accounts' )
        
    
    def AddSession( self, service_key, access_key ):
        
        with self._lock:
            
            account_key = HydrusGlobals.controller.Read( 'account_key_from_access_key', service_key, access_key )
            
            if account_key not in self._account_keys_to_accounts:
                
                account = HydrusGlobals.controller.Read( 'account', account_key )
                
                self._account_keys_to_accounts[ account_key ] = account
                
            
            account = self._account_keys_to_accounts[ account_key ]
            
            session_key = HydrusData.GenerateKey()
            
            self._account_keys_to_session_keys[ account_key ].add( session_key )
            
            now = HydrusData.GetNow()
            
            expires = now + HYDRUS_SESSION_LIFETIME
            
            HydrusGlobals.controller.Write( 'session', session_key, service_key, account_key, expires )
        
            self._service_keys_to_sessions[ service_key ][ session_key ] = ( account, expires )
            
        
        return ( session_key, expires )
        
    
    def GetAccount( self, service_key, session_key ):
        
        with self._lock:
            
            service_sessions = self._service_keys_to_sessions[ service_key ]
            
            if session_key in service_sessions:
                
                ( account, expires ) = service_sessions[ session_key ]
                
                if HydrusData.TimeHasPassed( expires ): del service_sessions[ session_key ]
                else: return account
                
            
            raise HydrusExceptions.SessionException( 'Did not find that session! Try again!' )
            
        
    
    def RefreshAccounts( self, service_key, account_keys ):
        
        with self._lock:
            
            for account_key in account_keys:
                
                account = HydrusGlobals.controller.Read( 'account', account_key )
                
                self._account_keys_to_accounts[ account_key ] = account
                
                if account_key in self._account_keys_to_session_keys:
                    
                    session_keys = self._account_keys_to_session_keys[ account_key ]
                    
                    for session_key in session_keys:
                        
                        ( old_account, expires ) = self._service_keys_to_sessions[ service_key ][ session_key ]
                        
                        self._service_keys_to_sessions[ service_key ][ session_key ] = ( account, expires )
                        
                    
                
            
        
    
    def RefreshAllAccounts( self ):
        
        with self._lock:
            
            self._service_keys_to_sessions = collections.defaultdict( dict )
            
            self._account_keys_to_session_keys = HydrusData.default_dict_set()
            
            self._account_keys_to_accounts = {}
            
            #
            
            existing_sessions = HydrusGlobals.controller.Read( 'sessions' )
            
            for ( session_key, service_key, account, expires ) in existing_sessions:
                
                account_key = account.GetAccountKey()
                
                self._service_keys_to_sessions[ service_key ][ session_key ] = ( account, expires )
                
                self._account_keys_to_session_keys[ account_key ].add( session_key )
                
                self._account_keys_to_accounts[ account_key ] = account
                
            
        
    