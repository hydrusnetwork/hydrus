import collections
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

HYDRUS_SESSION_EXPIRY_TIME = 30 * 86400

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
            
            expiry = now + HYDRUS_SESSION_EXPIRY_TIME
            
            self._sessions[ service_identifier ] = ( session_key, expiry )
            
            HC.app.Write( 'hydrus_session', service_identifier, session_key, expiry )
            
            return session_key
            
        
    
class HydrusSessionManagerServer():
    
    def __init__( self ):
        
        existing_sessions = HC.app.Read( 'sessions' )
        
        self._sessions = { ( session_key, service_identifier ) : ( account, expiry ) for ( session_key, service_identifier, account, expiry ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def AddSession( self, service_identifier, account ):
        
        session_key = os.urandom( 32 )
        
        now = HC.GetNow()
    
        expiry = now + HYDRUS_SESSION_EXPIRY_TIME
        
        HC.app.Write( 'session', session_key, service_identifier, account, expiry )
        
        with self._lock:
            
            self._sessions[ ( session_key, service_identifier ) ] = ( account, expiry )
            
        
        return ( session_key, expiry )
        
    
    def GetAccount( self, session_key, service_identifier ):
        
        now = HC.GetNow()
        
        with self._lock:
            
            if ( session_key, service_identifier ) in self._sessions:
                
                ( account, expiry ) = self._sessions[ ( session_key, service_identifier ) ]
                
                if now > expiry: del self._sessions[ ( session_key, service_identifier ) ]
                else: return account
                
            
            raise HydrusExceptions.SessionException()
            
        
    