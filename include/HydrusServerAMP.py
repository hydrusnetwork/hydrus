import collections
import Cookie
import hashlib
import httplib
import HydrusAudioHandling
import HydrusConstants as HC
import HydrusDocumentHandling
import HydrusExceptions
import HydrusFileHandling
import HydrusFlashHandling
import HydrusImageHandling
import HydrusServerResources
import os
import random
import ServerFiles
import SocketServer
import traceback
import urllib
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
from twisted.protocols import amp
import HydrusData
import HydrusGlobals
'''
class HydrusAMPCommand( amp.Command ):
    errors = {}
    errors[ HydrusExceptions.ForbiddenException ] = 'FORBIDDEN'
    errors[ HydrusExceptions.NetworkVersionException ] = 'NETWORK_VERSION'
    errors[ HydrusExceptions.NotFoundException ] = 'NOT_FOUND'
    errors[ HydrusExceptions.PermissionException ] = 'PERMISSION'
    errors[ HydrusExceptions.SessionException ] = 'SESSION'
    errors[ Exception ] = 'EXCEPTION'
    
# IMFile, for aes-encrypted file transfers, as negotiated over otr messages
# file_transfer_id (so we can match up the correct aes key)
# file (this is complicated -- AMP should be little things, right? I need to check max packet size.)
  # so, this should be blocks. a block_id and a block
# MMessageReceivedPing -- server to persistent client, saying someone just now sent you a message
class IMLoginPersistent( HydrusAMPCommand ):
    arguments = [ ( 'network_version', amp.Integer() ), ( 'session_key', amp.String() ) ]
    
class IMLoginTemporary( HydrusAMPCommand ):
    arguments = [ ( 'network_version', amp.Integer() ), ( 'identifier', amp.String() ), ( 'name', amp.String() ) ]

class IMMessageClient( HydrusAMPCommand ):
    arguments = [ ( 'identifier_from', amp.String() ), ( 'name_from', amp.String() ), ( 'identifier_to', amp.String() ), ( 'name_to', amp.String() ), ( 'message', amp.String() ) ]
    
class IMMessageServer( HydrusAMPCommand ):
    arguments = [ ( 'identifier_to', amp.String() ), ( 'name_to', amp.String() ), ( 'message', amp.String() ) ]
    
class IMSessionKey( HydrusAMPCommand ):
    arguments = [ ( 'access_key', amp.String() ), ( 'name', amp.String() ) ]
    response = [ ( 'session_key', amp.String() ) ]
    
class MPublicKey( HydrusAMPCommand ):
    arguments = [ ( 'identifier', amp.String() ) ]
    response = [ ( 'public_key', amp.String() ) ]
    
class HydrusAMP( amp.AMP ):
    
    def _errbackHandleError( self, failure ):
        
        HydrusData.Print( failure.getTraceback() )
        
        normal_errors = []
        
        normal_errors.append( HydrusExceptions.ForbiddenException )
        normal_errors.append( HydrusExceptions.NetworkVersionException )
        normal_errors.append( HydrusExceptions.NotFoundException )
        normal_errors.append( HydrusExceptions.PermissionException )
        normal_errors.append( HydrusExceptions.SessionException )
        
        if failure.type in normal_errors: failure.raiseException()
        else: raise Exception( failure.getTraceback() )
        
    
class MessagingClientProtocol( HydrusAMP ):
    
    def im_message( self, identifier_from, name_from, identifier_to, name_to, message ):
        
        def do_it( gumpf ):
            
            HydrusGlobals.controller.pub( 'im_message_received', identifier_from, name_from, identifier_to, name_to, message )
            
            return {}
            
        
        d = defer.Deferred()
        
        d.addCallback( do_it )
        
        d.addErrback( self._errbackHandleError )
        
        reactor.callLater( 0, d.callback, None )
        
        return d
        
    IMMessageClient.responder( im_message )
    
    def connectionLost( self, reason ):
        
        # report to ui that the connection is lost
        
        pass
        
    
class MessagingServiceProtocol( HydrusAMP ):
    
    def __init__( self ):
        
        amp.AMP.__init__( self )
        
        self._identifier = None
        self._name = None
        
    
    def _check_network_version( self, network_version ):
        
        if network_version != HC.NETWORK_VERSION:
            
            if network_version < HC.NETWORK_VERSION: message = 'Your client is out of date; please download the latest release.'
            else: message = 'This server is out of date; please ask its admin to update to the latest release.'
            
            message = 'Network version mismatch! This server\'s network version is ' + str( HC.NETWORK_VERSION ) + ', whereas your client\'s is ' + str( network_version ) + '! ' + message
            
            raise HydrusExceptions.NetworkVersionException( message )
            
        
    
    def im_login_persistent( self, network_version, session_key ):
        
        def do_it( gumpf ):
            
            self._check_network_version( network_version )
            
            session_manager = HydrusGlobals.controller.GetManager( 'messaging_sessions' )
            
            ( identifier, name ) = session_manager.GetIdentityAndName( self.factory.service_key, session_key )
            
            self._identifier = identifier
            self._name = name
            
            self.factory.AddConnection( True, self._identifier, self._name, self )
            
            return {}
            
        
        d = defer.Deferred()
        
        d.addCallback( do_it )
        
        d.addErrback( self._errbackHandleError )
        
        reactor.callLater( 0, d.callback, None )
        
        return d
        
    IMLoginPersistent.responder( im_login_persistent )
    
    def im_login_temporary( self, network_version, identifier, name ):
        
        def do_it( gumpf ):
            
            self._check_network_version( network_version )
            
            self._identifier = identifier
            self._name = name
            
            self.factory.AddConnection( False, self._identifier, self._name, self )
            
            return {}
            
        
        d = defer.Deferred()
        
        d.addCallback( do_it )
        
        d.addErrback( self._errbackHandleError )
        
        reactor.callLater( 0, d.callback, None )
        
        return d
        
    IMLoginTemporary.responder( im_login_temporary )
    
    def im_message( self, identifier_to, name_to, message ):
        
        def do_it( gumpf ):
            
            if self._identifier is None or self._name is None:
                
                raise Exception() # who the hell are you? pls temp login
                
            
            connection = self.factory.GetConnection( identifier_to, name_to )
            
            d = connection.callRemote( IMMessageClient, identifier_from = self._identifier, name_from = self._name, identifier_to = identifier_to, name_to = name_to, message = message )
            
            return d
            
        
        d = defer.Deferred()
        
        d.addCallback( do_it )
        
        d.addErrback( self._errbackHandleError )
        
        reactor.callLater( 0, d.callback, None )
        
        return d
        
    IMMessageServer.responder( im_message )
    
    def im_session_key( self, access_key, name ):
        
        def catch_session_key( session_key ): return { 'session_key' : session_key }
        
        def do_it( gumpf ):
            
            session_manager = HydrusGlobals.controller.GetManager( 'messaging_sessions' )
            
            d = deferToThread( session_manager.AddSession, self.factory.service_key, access_key, name )
            
            d.addCallback( catch_session_key )
            
            return d
            
        
        d = defer.Deferred()
        
        d.addCallback( do_it )
        
        d.addErrback( self._errbackHandleError )
        
        reactor.callLater( 0, d.callback, None )
        
        return d
        
    IMSessionKey.responder( im_session_key )
    
    def m_public_key( self, identifier ):
        
        # this will not be useful until we have normal messaging sorted
        
        public_key = 'public key'
        
        return { 'public_key' : public_key }
        
    MPublicKey.responder( m_public_key )
    
    def connectionLost( self, reason ):
        
        if self._identifier is not None: self.factory.RemoveConnection( self._identifier, self._name )
        
    '''
