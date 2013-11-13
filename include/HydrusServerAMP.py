import BaseHTTPServer
import ClientConstants as CC
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
import HydrusVideoHandling
import os
import random
import ServerConstants as SC
import SocketServer
import traceback
import urllib
import wx
import yaml
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
from twisted.protocols import amp

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
class IMLogin( HydrusAMPCommand ):
    arguments = [ ( 'session_key', amp.String() ) ]
    
class IMMessage( HydrusAMPCommand ):
    arguments = [ ( 'identifier_from', amp.String() ), ( 'identifier_to', amp.String() ), ( 'message', amp.String() ) ]
    
class IMSessionKey( HydrusAMPCommand ):
    arguments = [ ( 'access_key', amp.String() ) ]
    response = [ ( 'session_key', amp.String() ) ]
    
class MPublicKey( HydrusAMPCommand ):
    arguments = [ ( 'identifier', amp.String() ) ]
    response = [ ( 'public_key', amp.String() ) ]
    
class MessagingServiceProtocol( amp.AMP ):
    
    def im_login( self, session_key ):
        
        # check session_key.
        # if it is good, stick this connection on the login manager
        # else error
        
        return {}
        
    IMLogin.responder( im_login )
    
    def im_message( self, identifier_from, identifier_to, message ):
        
        # get connection for identifier_to from larger, failing appropriately
        # if we fail, we should probably log the _to out, right?
        
        # connection.callRemote( IMMessage, identifier_from = identifier_from, identifier_to = identifier_to, message = message )
        # this returns a deferred, so set up a 'return {}' deferred.
        
        return {}
        
    IMMessage.responder( im_message )
    
    def im_session_key( self, access_key ):
        
        session_key = os.urandom( 32 )
        
        return { 'session_key' : session_key }
        
    IMSessionKey.responder( im_session_key )
    
    def m_public_key( self, identifier ):
        
        # this will not be useful until we have normal messaging sorted
        
        public_key = 'public key'
        
        return { 'public_key' : public_key }
        
    MPublicKey.responder( m_public_key )
    
    def connectionLost( self, reason ):
        
        # delete this connection from the login stuffs.
        
        pass
        
    
class MessagingClientProtocol( amp.AMP ):
    
    def im_message( self, identifier_from, identifier_to, message ):
        
        # send these args on to the messaging manager, which will:
          # start a context, if needed
          # spawn a gui prompt/window to start a convo, if needed
          # queue the message through to the appropriate context
          # maybe the context should spam up to the ui, prob in a pubsub; whatever.
        
        pass
        
    IMMessage.responder( im_message )