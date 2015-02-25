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
import wx
import yaml
from twisted.internet.threads import deferToThread

HYDRUS_SESSION_LIFETIME = 30 * 86400

class HydrusMessagingSessionManagerServer( object ):
    
    def __init__( self ):
        
        existing_sessions = HC.app.Read( 'messaging_sessions' )
        
        self._service_keys_to_sessions = collections.defaultdict( dict )
        
        for ( service_key, session_tuples ) in existing_sessions:
            
            self._service_keys_to_sessions[ service_key ] = { session_key : ( account, name, expires ) for ( session_key, account, name, expires ) in session_tuples }
            
        
        self._lock = threading.Lock()
        
    
    def GetIdentityAndName( self, service_key, session_key ):
        
        with self._lock:
            
            if session_key not in self._service_keys_to_sessions[ service_key ]: raise HydrusExceptions.SessionException( 'Did not find that session!' )
            else:
                
                ( account, name, expires ) = self._service_keys_to_sessions[ service_key ][ session_key ]
                
                now = HC.GetNow()
                
                if now > expires:
                    
                    del self._service_keys_to_sessions[ service_key ][ session_key ]
                    
                    raise HydrusExceptions.SessionException( 'Session expired!' )
                    
                
                return ( account.GetAccountKey(), name )
                
            
        
    
    def AddSession( self, service_key, access_key, name ):
        
        session_key = os.urandom( 32 )
        
        account_key = HC.app.Read( 'account_key_from_access_key', service_key, access_key )
        
        account = HC.app.Read( 'account', service_key, account_key )
        
        now = HC.GetNow()
        
        expires = now + HYDRUS_SESSION_LIFETIME
        
        with self._lock: self._service_keys_to_sessions[ service_key ][ session_key ] = ( account, name, expires )
        
        HC.app.Write( 'messaging_session', service_key, session_key, account_key, name, expires )
        
        return session_key
        
    
class HydrusSessionManagerClient( object ):
    
    def __init__( self ):
        
        existing_sessions = HC.app.Read( 'hydrus_sessions' )
        
        self._service_keys_to_sessions = { service_key : ( session_key, expires ) for ( service_key, session_key, expires ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def DeleteSessionKey( self, service_key ):
        
        with self._lock:
            
            HC.app.Write( 'delete_hydrus_session_key', service_key )
            
            if service_key in self._service_keys_to_sessions: del self._service_keys_to_sessions[ service_key ]
            
        
    
    def GetSessionKey( self, service_key ):
        
        now = HC.GetNow()
        
        with self._lock:
            
            if service_key in self._service_keys_to_sessions:
                
                ( session_key, expires ) = self._service_keys_to_sessions[ service_key ]
                
                if now + 600 > expires: del self._service_keys_to_sessions[ service_key ]
                else: return session_key
                
            
            # session key expired or not found
            
            service = HC.app.GetManager( 'services' ).GetService( service_key )
            
            ( response, cookies ) = service.Request( HC.GET, 'session_key', return_cookies = True )
            
            try: session_key = cookies[ 'session_key' ].decode( 'hex' )
            except: raise Exception( 'Service did not return a session key!' )
            
            expires = now + HYDRUS_SESSION_LIFETIME
            
            self._service_keys_to_sessions[ service_key ] = ( session_key, expires )
            
            HC.app.Write( 'hydrus_session', service_key, session_key, expires )
            
            return session_key
            
        
    
class HydrusSessionManagerServer( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self.RefreshAllAccounts()
        
        HC.pubsub.sub( self, 'RefreshAllAccounts', 'update_all_session_accounts' )
        
    
    def AddSession( self, service_key, access_key ):
        
        with self._lock:
            
            account_key = HC.app.Read( 'account_key_from_access_key', service_key, access_key )
            
            if account_key not in self._account_keys_to_accounts:
                
                account = HC.app.Read( 'account', account_key )
                
                self._account_keys_to_accounts[ account_key ] = account
                
            
            account = self._account_keys_to_accounts[ account_key ]
            
            session_key = os.urandom( 32 )
            
            self._account_keys_to_session_keys[ account_key ].add( session_key )
            
            now = HC.GetNow()
            
            expires = now + HYDRUS_SESSION_LIFETIME
            
            HC.app.Write( 'session', session_key, service_key, account_key, expires )
        
            self._service_keys_to_sessions[ service_key ][ session_key ] = ( account, expires )
            
        
        return ( session_key, expires )
        
    
    def GetAccount( self, service_key, session_key ):
        
        with self._lock:
            
            service_sessions = self._service_keys_to_sessions[ service_key ]
            
            if session_key in service_sessions:
                
                ( account, expires ) = service_sessions[ session_key ]
                
                now = HC.GetNow()
                
                if now > expires: del service_sessions[ session_key ]
                else: return account
                
            
            raise HydrusExceptions.SessionException()
            
        
    
    def RefreshAccounts( self, service_key, account_keys ):
        
        with self._lock:
            
            for account_key in account_keys:
                
                account = HC.app.Read( 'account', account_key )
                
                self._account_keys_to_accounts[ account_key ] = account
                
                if account_key in self._account_keys_to_session_keys:
                    
                    session_keys = self._account_keys_to_session_keys[ account_key ]
                    
                    for session_key in session_keys:
                        
                        ( old_account, expires ) = self._service_keys_to_sessions[ service_key ][ session_key ]
                        
                        self._service_keys_to_sessions[ service_key ][ session_key ] = ( account, expires )
                        
                    
                
            
        
    
    def RefreshAllAccounts( self ):
        
        with self._lock:
            
            self._service_keys_to_sessions = collections.defaultdict( dict )
            
            self._account_keys_to_session_keys = HC.default_dict_set()
            
            self._account_keys_to_accounts = {}
            
            #
            
            existing_sessions = HC.app.Read( 'sessions' )
            
            for ( session_key, service_key, account, expires ) in existing_sessions:
                
                account_key = account.GetAccountKey()
                
                self._service_keys_to_sessions[ service_key ][ session_key ] = ( account, expires )
                
                self._account_keys_to_session_keys[ account_key ].add( session_key )
                
                self._account_keys_to_accounts[ account_key ] = account
                
            
        
    
class WebSessionManagerClient( object ):
    
    def __init__( self ):
        
        existing_sessions = HC.app.Read( 'web_sessions' )
        
        self._names_to_sessions = { name : ( cookies, expires ) for ( name, cookies, expires ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def GetCookies( self, name ):
        
        now = HC.GetNow()
        
        with self._lock:
            
            if name in self._names_to_sessions:
                
                ( cookies, expires ) = self._names_to_sessions[ name ]
                
                if now + 300 > expires: del self._names_to_sessions[ name ]
                else: return cookies
                
            
            # name not found, or expired
            
            if name == 'hentai foundry':
                
                ( response_gumpf, cookies ) = HC.http.Request( HC.GET, 'http://www.hentai-foundry.com/?enterAgree=1', return_cookies = True )
                
                expires = now + 60 * 60
                
            elif name == 'pixiv':
                
                ( id, password ) = HC.app.Read( 'pixiv_account' )
                
                if id == '' and password == '':
                    
                    raise Exception( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                    
                
                form_fields = {}
                
                form_fields[ 'mode' ] = 'login'
                form_fields[ 'pixiv_id' ] = id
                form_fields[ 'pass' ] = password
                form_fields[ 'skip' ] = '1'
                
                body = urllib.urlencode( form_fields )
                
                headers = {}
                headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
                
                ( response_gumpf, cookies ) = HC.http.Request( HC.POST, 'http://www.pixiv.net/login.php', request_headers = headers, body = body, return_cookies = True )
                
                # _ only given to logged in php sessions
                if 'PHPSESSID' not in cookies or '_' not in cookies[ 'PHPSESSID' ]: raise Exception( 'Pixiv login credentials not accepted!' )
                
                expires = now + 30 * 86400
                
            
            self._names_to_sessions[ name ] = ( cookies, expires )
            
            HC.app.Write( 'web_session', name, cookies, expires )
            
            return cookies
            
        
    