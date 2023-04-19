import collections
import hashlib
import threading

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

HYDRUS_SESSION_LIFETIME = 30 * 86400

class HydrusSessionManagerServer( object ):
    
    def __init__( self ):
        
        self._lock = threading.Lock()
        
        self.RefreshAllAccounts()
        
        HG.controller.sub( self, 'RefreshAccounts', 'update_session_accounts' )
        HG.controller.sub( self, 'RefreshAllAccounts', 'update_all_session_accounts' )
        
    
    def _GetAccountFromAccountKey( self, service_key, account_key ):
        
        account_keys_to_accounts = self._service_keys_to_account_keys_to_accounts[ service_key ]
        
        if account_key not in account_keys_to_accounts:
            
            if HG.server_busy.locked():
                
                raise HydrusExceptions.ServerBusyException( 'Sorry, server is busy and cannot fetch account data right now!' )
                
            
            account = HG.controller.Read( 'account', service_key, account_key )
            
            account_keys_to_accounts[ account_key ] = account
            
        
        account = account_keys_to_accounts[ account_key ]
        
        return account
        
    
    def _GetAccountKeyFromAccessKey( self, service_key, access_key ):
        
        hashed_access_key = hashlib.sha256( access_key ).digest()
        
        if hashed_access_key not in self._service_keys_to_hashed_access_keys_to_account_keys[ service_key ]:
            
            if HG.server_busy.locked():
                
                raise HydrusExceptions.ServerBusyException( 'Sorry, server is busy and cannot fetch account id data right now!' )
                
            
            account_key = HG.controller.Read( 'account_key_from_access_key', service_key, access_key )
            
            self._service_keys_to_hashed_access_keys_to_account_keys[ service_key ][ hashed_access_key ] = account_key
            
        
        account_key = self._service_keys_to_hashed_access_keys_to_account_keys[ service_key ][ hashed_access_key ]
        
        return account_key
        
    
    def AddSession( self, service_key, access_key ):
        
        with self._lock:
            
            account_key = self._GetAccountKeyFromAccessKey( service_key, access_key )
            
            account = self._GetAccountFromAccountKey( service_key, account_key )
            
            session_key = HydrusData.GenerateKey()
            
            now = HydrusTime.GetNow()
            
            expires = now + HYDRUS_SESSION_LIFETIME
            
            HG.controller.Write( 'session', session_key, service_key, account_key, expires )
            
            self._service_keys_to_session_keys_to_sessions[ service_key ][ session_key ] = ( account_key, expires )
            
            return ( session_key, expires )
            
        
    
    def GetAccount( self, service_key, session_key ):
        
        with self._lock:
            
            session_keys_to_sessions = self._service_keys_to_session_keys_to_sessions[ service_key ]
            
            if session_key in session_keys_to_sessions:
                
                ( account_key, expires ) = session_keys_to_sessions[ session_key ]
                
                if HydrusTime.TimeHasPassed( expires ):
                    
                    del session_keys_to_sessions[ session_key ]
                    
                else:
                    
                    account = self._service_keys_to_account_keys_to_accounts[ service_key ][ account_key ]
                    
                    return account
                    
                
            
            raise HydrusExceptions.SessionException( 'Did not find that session! Try again!' )
            
        
    
    def GetAccountFromAccessKey( self, service_key, access_key ):
        
        with self._lock:
            
            account_key = self._GetAccountKeyFromAccessKey( service_key, access_key )
            
            account = self._GetAccountFromAccountKey( service_key, account_key )
            
            return account
            
        
    
    def GetDirtyAccounts( self ):
        
        with self._lock:
            
            service_keys_to_dirty_accounts = {}
            
            for ( service_key, account_keys_to_accounts ) in self._service_keys_to_account_keys_to_accounts.items():
                
                dirty_accounts = [ account_key for account_key in account_keys_to_accounts.values() if account_key.IsDirty() ]
                
                if len( dirty_accounts ) > 0:
                    
                    service_keys_to_dirty_accounts[ service_key ] = dirty_accounts
                    
                
            
            return service_keys_to_dirty_accounts
            
        
    
    def RefreshAccounts( self, service_key, account_keys = None ):
        
        with self._lock:
            
            account_keys_to_accounts = self._service_keys_to_account_keys_to_accounts[ service_key ]
            
            if account_keys is None:
                
                account_keys = list( account_keys_to_accounts.keys() )
                
            
            for account_key in account_keys:
                
                account = HG.controller.Read( 'account', service_key, account_key )
                
                account_keys_to_accounts[ account_key ] = account
                
            
        
    
    def RefreshAllAccounts( self, service_key = None ):
        
        with self._lock:
            
            if service_key is None:
                
                self._service_keys_to_session_keys_to_sessions = collections.defaultdict( dict )
                
                self._service_keys_to_account_keys_to_accounts = collections.defaultdict( dict )
                
                self._service_keys_to_hashed_access_keys_to_account_keys = collections.defaultdict( dict )
                
                existing_sessions = HG.controller.Read( 'sessions' )
                
            else:
                
                del self._service_keys_to_session_keys_to_sessions[ service_key ]
                
                del self._service_keys_to_account_keys_to_accounts[ service_key ]
                
                del self._service_keys_to_hashed_access_keys_to_account_keys[ service_key ]
                
                existing_sessions = HG.controller.Read( 'sessions', service_key )
                
            
            for ( session_key, service_key, account, hashed_access_key, expires ) in existing_sessions:
                
                account_key = account.GetAccountKey()
                
                self._service_keys_to_session_keys_to_sessions[ service_key ][ session_key ] = ( account_key, expires )
                
                if account_key not in self._service_keys_to_account_keys_to_accounts:
                    
                    self._service_keys_to_account_keys_to_accounts[ service_key ][ account_key ] = account
                    
                
                if hashed_access_key not in self._service_keys_to_hashed_access_keys_to_account_keys:
                    
                    self._service_keys_to_hashed_access_keys_to_account_keys[ service_key ][ hashed_access_key ] = account_key
                    
                
            
        
    
    def UpdateAccounts( self, service_key, accounts ):
        
        with self._lock:
            
            account_keys_to_accounts = self._service_keys_to_account_keys_to_accounts[ service_key ]
            
            for account in accounts:
                
                account_keys_to_accounts[ account.GetAccountKey() ] = account
                
            
        
