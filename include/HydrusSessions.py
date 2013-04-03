import collections
import httplib
import HydrusConstants as HC
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

class HydrusSessionManagerClient():
    
    def __init__( self ):
        
        existing_sessions = wx.GetApp().Read( 'hydrus_sessions' )
        
        self._sessions = { service_identifier : ( session_key, expiry ) for ( service_identifier, session_key, expiry ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def DeleteSessionKey( self, service_identifier ):
        
        with self._lock:
            
            wx.GetApp().Write( 'delete_hydrus_session_key', service_identifier )
            
            del self._sessions[ service_identifier ]
            
        
    
    def GetSessionKey( self, service_identifier ):
        
        now = int( time.time() )
        
        with self._lock:
            
            if service_identifier in self._sessions:
                
                ( session_key, expiry ) = self._sessions[ service_identifier ]
                
                if now + 600 > expiry: del self._sessions[ service_identifier ]
                else: return session_key
                
            
            # session key expired or not found
            
            service = wx.GetApp().Read( 'service', service_identifier )
            
            connection = service.GetConnection()
            
            connection.Get( 'session_key' )
            
            cookies = connection.GetCookies()
            
            try: session_key = cookies[ 'session_key' ].decode( 'hex' )
            except: raise Exception( 'Service did not return a session key!' )
            
            expiry = now + 30 * 86400
            
            self._sessions[ service_identifier ] = ( session_key, expiry )
            
            wx.GetApp().Write( 'hydrus_session', service_identifier, session_key, expiry )
            
            return session_key
            
        
    
class HydrusSessionManagerServer():
    
    def __init__( self ):
        
        existing_sessions = wx.GetApp().GetDB().Read( 'sessions', HC.HIGH_PRIORITY )
        
        self._sessions = { ( session_key, service_identifier ) : ( account_identifier, expiry ) for ( session_key, service_identifier, account_identifier, expiry ) in existing_sessions }
        
        self._lock = threading.Lock()
        
    
    def AddSession( self, session_key, service_identifier, account_identifier, expiry ):
        
        wx.GetApp().GetDB().Write( 'session', HC.HIGH_PRIORITY, session_key, service_identifier, account_identifier, expiry )
        
        self._sessions[ ( session_key, service_identifier ) ] = ( account_identifier, expiry )
        
    
    def GetAccountIdentifier( self, session_key, service_identifier ):
        
        now = int( time.time() )
        
        with self._lock:
            
            if ( session_key, service_identifier ) in self._sessions:
                
                ( account_identifier, expiry ) = self._sessions[ ( session_key, service_identifier ) ]
                
                if now > expiry: del self._sessions[ ( session_key, service_identifier ) ]
                else: return account_identifier
                
            
            # session not found, or expired
            
            raise HC.SessionException()
            
        
    