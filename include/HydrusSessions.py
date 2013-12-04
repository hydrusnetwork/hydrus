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
import wx
import yaml
from twisted.internet.threads import deferToThread

HYDRUS_SESSION_LIFETIME = 30 * 86400

class HydrusMessagingSessionManagerServer():
    
    def __init__( self ):
        
        existing_sessions = HC.app.Read( 'messaging_sessions' )
        
        self._sessions = collections.defaultdict( dict )
        
        for ( service_identifier, session_tuples ) in existing_sessions:
            
            self._sessions[ service_identifier ] = { session_key : ( account, identifier, name, expiry ) for ( session_Key, account, identifier, name, expiry ) in session_tuples }
            
        
        self._lock = threading.Lock()
        
    
    def GetIdentityAndName( self, service_identifier, session_key ):
        
        with self._lock:
            
            if session_key not in self._sessions[ service_identifier ]: raise HydrusExceptions.SessionException( 'Did not find that session!' )
            else:
                
                ( account, identity, name, expiry ) = self._sessions[ service_identifier ][ session_key ]
                
                now = HC.GetNow()
                
                if now > expiry:
                    
                    del self._sessions[ service_identifier ][ session_key ]
                    
                    raise HydrusExceptions.SessionException( 'Session expired!' )
                    
                
                return ( identity, name )
                
            
        
    
    def AddSession( self, service_identifier, access_key, name ):
        
        session_key = os.urandom( 32 )
        
        account_identifier = HC.AccountIdentifier( access_key = access_key )
        
        account = HC.app.Read( 'account', service_identifier, account_identifier )
        
        account_identifier = account.GetAccountIdentifier() # for better account_id based identifier
        
        identity = hashlib.sha256( access_key ).digest()
        
        now = HC.GetNow()
        
        expiry = now + HYDRUS_SESSION_LIFETIME
        
        with self._lock:
            
            self._sessions[ service_identifier ][ session_key ] = ( account, identity, name, expiry )
            
        
        HC.app.Write( 'messaging_session', service_identifier, session_key, account, identity, name, expiry )
        
        return session_key
        
    
class HydrusSessionManagerClient():
    
    def __init__( self ):
        
        existing_sessions = HC.app.Read( 'hydrus_sessions' )
        
        self._sessions = { service_identifier : ( session_key, expiry ) for ( service_identifier, session_key, expiry ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def DeleteSessionKey( self, service_identifier ):
        
        with self._lock:
            
            HC.app.Write( 'delete_hydrus_session_key', service_identifier )
            
            del self._sessions[ service_identifier ]
            
        
    
    def GetSessionKey( self, service_identifier ):
        
        now = HC.GetNow()
        
        with self._lock:
            
            if service_identifier in self._sessions:
                
                ( session_key, expiry ) = self._sessions[ service_identifier ]
                
                if now + 600 > expiry: del self._sessions[ service_identifier ]
                else: return session_key
                
            
            # session key expired or not found
            
            service = HC.app.Read( 'service', service_identifier )
            
            connection = service.GetConnection()
            
            connection.Get( 'session_key' )
            
            cookies = connection.GetCookies()
            
            try: session_key = cookies[ 'session_key' ].decode( 'hex' )
            except: raise Exception( 'Service did not return a session key!' )
            
            expiry = now + HYDRUS_SESSION_LIFETIME
            
            self._sessions[ service_identifier ] = ( session_key, expiry )
            
            HC.app.Write( 'hydrus_session', service_identifier, session_key, expiry )
            
            return session_key
            
        
    
class HydrusSessionManagerServer():
    
    def __init__( self ):
        
        existing_sessions = HC.app.Read( 'sessions' )
        
        self._account_ids_to_session_keys = collections.defaultdict( HC.default_dict_set )
        
        self._account_cache = collections.defaultdict( dict )
        
        self._sessions = collections.defaultdict( dict )
        
        for ( session_key, service_identifier, account, expiry ) in existing_sessions:
            
            self._sessions[ service_identifier ][ session_key ] = ( account, expiry )
            
            account_id = account.GetAccountId()
            
            self._account_ids_to_session_keys[ service_identifier ][ account_id ].add( session_key )
            
        
        self._lock = threading.Lock()
        
        HC.pubsub.sub( self, 'RefreshAllAccounts', 'update_all_session_accounts' )
        
    
    def AddSession( self, service_identifier, account_identifier ):
        
        with self._lock:
            
            if account_identifier not in self._account_cache[ service_identifier ]:
                
                account = HC.app.Read( 'account', service_identifier, account_identifier )
                
                account_identifier = account.GetAccountIdentifier() # get the account_id based account_identifier
                
                if account_identifier not in self._account_cache[ service_identifier ]:
                    self._account_cache[ service_identifier ][ account_identifier ] = account
                
            
            account = self._account_cache[ service_identifier ][ account_identifier ]
            
            account_id = account.GetAccountId()
            
            session_key = os.urandom( 32 )
            
            self._account_ids_to_session_keys[ service_identifier ][ account_id ].add( session_key )
            
            now = HC.GetNow()
            
            expiry = now + HYDRUS_SESSION_LIFETIME
            
            HC.app.Write( 'session', session_key, service_identifier, account, expiry )
        
            self._sessions[ service_identifier ][ session_key ] = ( account, expiry )
            
        
        return ( session_key, expiry )
        
    
    def GetAccount( self, service_identifier, session_key ):
        
        now = HC.GetNow()
        
        with self._lock:
            
            if session_key in self._sessions[ service_identifier ]:
                
                ( account, expiry ) = self._sessions[ service_identifier ][ session_key ]
                
                if expiry is not None and now > expiry: del self._sessions[ service_identifier ][ session_key ]
                else: return account
                
            
            raise HydrusExceptions.SessionException()
            
        
    
    def RefreshAccounts( self, service_identifier, account_identifiers ):
        
        with self._lock:
            
            for account_identifier in account_identifiers:
                
                account = HC.app.Read( 'account', service_identifier, account_identifier )
                
                account_identifier = account.GetAccountIdentifier() # get the account_id based account_identifier
                
                self._account_cache[ service_identifier ][ account_identifier ] = account
                
                account_id = account.GetAccountId()
                
                if account_id in self._account_ids_to_session_keys[ service_identifier ]:
                    
                    session_keys = self._account_ids_to_session_keys[ service_identifier ][ account_id ]
                    
                    for session_key in session_keys:
                        
                        ( old_account, expiry ) = self._sessions[ service_identifier ][ session_key ]
                        
                        self._sessions[ service_identifier ][ session_key ] = ( account, expiry )
                        
                    
                
            
        
    
    def RefreshAllAccounts( self ):
        
        existing_sessions = HC.app.Read( 'sessions' )
        
        self._account_ids_to_session_keys = collections.defaultdict( HC.default_dict_set )
        
        self._account_cache = collections.defaultdict( dict )
        
        self._sessions = collections.defaultdict( dict )
        
        for ( session_key, service_identifier, account, expiry ) in existing_sessions:
            
            self._sessions[ service_identifier ][ session_key ] = ( account, expiry )
            
            account_id = account.GetAccountId()
            
            self._account_ids_to_session_keys[ service_identifier ][ account_id ].add( session_key )
            
        
    
class WebSessionManagerClient():
    
    def __init__( self ):
        
        existing_sessions = HC.app.Read( 'web_sessions' )
        
        self._sessions = { name : ( cookies, expiry ) for ( name, cookies, expiry ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def GetCookies( self, name ):
        
        now = HC.GetNow()
        
        with self._lock:
            
            if name in self._sessions:
                
                ( cookies, expiry ) = self._sessions[ name ]
                
                if now + 300 > expiry: del self._sessions[ name ]
                else: return cookies
                
            
            # name not found, or expired
            
            if name == 'hentai foundry':
                
                connection = HC.get_connection( url = 'http://www.hentai-foundry.com', accept_cookies = True )
                
                # this establishes the php session cookie, the csrf cookie, and tells hf that we are 18 years of age
                connection.request( 'GET', '/?enterAgree=1' )
                
                cookies = connection.GetCookies()
                
                expiry = now + 60 * 60
                
            elif name == 'pixiv':
                
                ( id, password ) = HC.app.Read( 'pixiv_account' )
                
                if id == '' and password == '':
                    
                    raise Exception( 'You need to set up your pixiv credentials in services->manage pixiv account.' )
                    
                
                connection = HC.get_connection( url = 'http://www.pixiv.net', accept_cookies = True )
                
                form_fields = {}
                
                form_fields[ 'mode' ] = 'login'
                form_fields[ 'pixiv_id' ] = id
                form_fields[ 'pass' ] = password
                form_fields[ 'skip' ] = '1'
                
                body = urllib.urlencode( form_fields )
                
                headers = {}
                headers[ 'Content-Type' ] = 'application/x-www-form-urlencoded'
                
                # this logs in and establishes the php session cookie
                response = connection.request( 'POST', '/login.php', headers = headers, body = body, follow_redirects = False )
                
                cookies = connection.GetCookies()
                
                # _ only given to logged in php sessions
                if 'PHPSESSID' not in cookies or '_' not in cookies[ 'PHPSESSID' ]: raise Exception( 'Login credentials not accepted!' )
                
                expiry = now + 30 * 86400
                
            
            self._sessions[ name ] = ( cookies, expiry )
            
            HC.app.Write( 'web_session', name, cookies, expiry )
            
            return cookies
            
        
    