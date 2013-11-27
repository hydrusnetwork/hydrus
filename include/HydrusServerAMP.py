import BaseHTTPServer
import ClientConstants as CC
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
# MMessageReceivedPing -- server to persistent client, saying someone just now sent you a message
class IMLoginPersistent( HydrusAMPCommand ):
    arguments = [ ( 'session_key', amp.String() ) ]
    
class IMLoginTemporary( HydrusAMPCommand ):
    arguments = [ ( 'identifier', amp.String() ), ( 'name', amp.String() ) ]

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
    