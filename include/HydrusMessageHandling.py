import Crypto.Hash.SHA256
import Crypto.Signature.PKCS1_v1_5
import hashlib
import HydrusConstants as HC
import HydrusEncryption
import HydrusServer
import os
import potr
import time
import traceback
import yaml
import zlib
from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator
import HydrusData
'''
def PackageStatusForDelivery( status, public_key_text ):
    
    public_key = HydrusEncryption.TextToKey( public_key_text )
    
    yamled = yaml.safe_dump( status )
    
    gzipped = zlib.compress( yamled )
    
    encrypted_gzipped = HydrusEncryption.EncryptPKCS( public_key, gzipped )
    
    return encrypted_gzipped
    
def UnpackageDeliveredStatus( encrypted_gzipped, private_key_text ):
    
    private_key = HydrusEncryption.TextToKey( private_key_text )
    
    gzipped = HydrusEncryption.DecryptPKCS( private_key, encrypted_gzipped )
    
    yamled = zlib.decompress( gzipped )
    
    status = yaml.safe_load( yamled )
    
    return status
    
def PackageMessageForDelivery( message_object, public_key_text ):
    
    public_key = HydrusEncryption.TextToKey( public_key_text )
    
    yamled = yaml.safe_dump( message_object )
    
    gzipped = zlib.compress( yamled )
    
    ( aes_key, iv ) = HydrusEncryption.GenerateAESKeyAndIV()
    
    encrypted_aes_key = HydrusEncryption.EncryptPKCS( public_key, aes_key + iv )
    
    encrypted_message = HydrusEncryption.EncryptAES( aes_key, iv, gzipped )
    
    whole_encrypted_message = encrypted_aes_key + encrypted_message
    
    return whole_encrypted_message
    
def UnpackageDeliveredMessage( whole_encrypted_message, private_key_text ):
    
    private_key = HydrusEncryption.TextToKey( private_key_text )
    
    encrypted_aes_key = whole_encrypted_message[:256]
    
    aes_key_and_iv = HydrusEncryption.DecryptPKCS( private_key, encrypted_aes_key )
    
    aes_key = aes_key_and_iv[:32]
    
    iv = aes_key_and_iv[32:]
    
    encrypted_message = whole_encrypted_message[256:]
    
    gzipped = HydrusEncryption.DecryptAES( aes_key, iv, encrypted_message )
    
    yamled = zlib.decompress( gzipped )
    
    message = yaml.safe_load( yamled )
    
    return message
    
class Message( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!Message'
    
    def __init__( self, conversation_key, contact_from, contacts_to, subject, body, timestamp, files = None, private_key = None ):
        
        if files is None: files = []
        
        if contact_from is not None and contact_from.GetName() == 'Anonymous': contact_from = None
        
        self._contact_from = contact_from
        self._contacts_to = contacts_to
        self._subject = subject
        self._body = body
        self._files = files
        
        self._timestamp = timestamp
        
        self._conversation_key = conversation_key
        
        hash_object = self._GetHashObject()
        
        if private_key is None: self._signature = None
        else:
            
            private_key_object = HydrusEncryption.TextToKey( private_key )
            
            signer = Crypto.Signature.PKCS1_v1_5.new( private_key_object )
            
            self._signature = signer.sign( hash_object )
            
        
        self._message_key = hash_object.digest()
        
    
    def _GetHashObject( self ):
        
        message = ''
        
        if self._contact_from is not None: message += yaml.safe_dump( self._contact_from.GetPublicKey() )
        
        contact_to_public_keys = [ contact_to.GetPublicKey() for contact_to in self._contacts_to ]
        
        contact_to_public_keys.sort()
        
        if type( self._subject ) == unicode: subject_text = self._subject.encode( 'utf-8' )
        else: subject_text = self._subject
        
        if type( self._body ) == unicode: body_text = self._body.encode( 'utf-8' )
        else: body_text = self._body
        
        message += ''.join( [ yaml.safe_dump( public_key ) for public_key in contact_to_public_keys ] ) + subject_text + body_text + ''.join( self._files ) + HydrusData.ToUnicode( self._conversation_key ) + HydrusData.ToUnicode( self._timestamp )
        
        hash_object = Crypto.Hash.SHA256.new( message )
        
        return hash_object
        
    
    def GetContactFrom( self ): return self._contact_from
    
    def GetContactsTo( self ): return self._contacts_to
    
    def GetInfo( self ): 
        
        if self._conversation_key is None: conversation_key = self._message_key
        else: conversation_key = self._conversation_key
        
        return ( self._contact_from, self._contacts_to, self._message_key, conversation_key, self._timestamp, self._subject, self._body, self._files )
        
    
    def GetMessageKey( self ): return self._message_key
    
    def VerifyIsFromCorrectPerson( self, public_key_text ):
        
        public_key = HydrusEncryption.TextToKey( public_key_text )
        
        hash_object = self._GetHashObject()
        
        self._message_key = hash_object.digest()
        
        verifier = Crypto.Signature.PKCS1_v1_5.new( public_key )
        
        return verifier.verify( hash_object, self._signature )
        
    
# here begins the new stuff, I'm pretty sure

class Identity( object ): # should be a yamlable object
    
    def __init__( self ):
        
        # no name, right? we associate names and addresses with the identity, but the id only has keys
        
        # store key_type -> key
        # hence need a key_type enum
        
        pass
        
    
class IMManager( object ):
    
    def __init__( self ):
        
        self._accounts = {}
        self._contexts = {}
        self._persistent_connections = {}
        self._temporary_connections = {}
        
        # go fetch all accounts from the db
        
        # set up many pubsubs
        
        # start up some sort of daemon to keep our accounts logged in
        
        pass
        
    
    def _GetContext( self, identifier_local, name_local, identifier_remote, name_remote ):
        
        if ( identifier_remote, name_remote ) not in self._contexts[ identifier_local ]:
            
            account = self._accounts[ ( identifier_local, name_local ) ]
            
            context = HydrusEncryption.HydrusOTRContext( account, identifier_remote, name_remote )
            
            self._contexts[ ( identifier_local, name_local, identifier_remote, name_remote ) ] = context
            
        
        context = self._contexts[ identifier_local ][ ( identifier_remote, name_remote ) ]
        
        return context
        
    
    def LoginPersistentConnections( self ):
        
        # this is on a daemon thread, so move to twisted
        
        for ( identifier, name ) in self._accounts.keys():
            
            if ( identifier, name ) not in self._persistent_connections:
                
                # get host, port for that identity
                
                creator = ClientCreator( reactor, HydrusServerAMP.MessagingClientProtocol )
                
                deferred = creator.connectTCP( host, port )
                
                # deferred is called with the connection, or an error
                # callRemote to register with session key and whatnot
                
                self._persistent_connections[ ( identifier, name ) ] = connection
                
            
        
    
    def ReceiveMessage( self, identifier_from, name_from, identifier_to, name_to, message ):
        
        # currently on wx loop
        # move it to the twisted loop
        
        if ( identifier_from, name_from, identifier_to, name_to ) not in self._temporary_connections:
            
            self._temporary_connections[ ( identifier_from, name_from, identifier_to, name_to ) ] = self._persistent_connections[ ( identifier_to, name_to ) ]
            # this should have a better error, if the _to doesn't exist
            # we should really just disregard it, and any other weirdness
            
        
        context = self._GetContext( identifier_to, name_to, identifier_from, name_from )
        
        response = context.receiveMessage( message )
        
        if response is not None:
            
            ( decrypted_message, gumpf ) = response
            
            message_object = yaml.safe_load( decrypted_message )
            
            # do the pubsub
            
        
    
    def RemovePersistentConnection( self, identifier, name ):
        
        # if it is still alive, loseConnection or whatever.
        # remove it
        # pubsub the login daemon
        
        pass
        
    
    def RemoveTemporaryConnection( self, identifier_from, name_from, identifier_to, name_to ):
        
        # if it is still alive, loseConnection or whatever.
        # remove it
        
        pass
        
    
    def SendMessage( self, identifier_from, name_from, identifier_to, name_to, message ):
        
        context = self._GetContext( identifier_from, name_from, identifier_to, name_to )
        
        context.sendMessage( potr.context.FRAGMENT_SEND_ALL, message )
        
    
    def SendEncryptedMessage( self, identifier_from, name_from, identifier_to, name_to, message ):
        
        # currently on wx loop
        # move it to the twisted loop
        
        connection = self._temporary_connections[ ( identifier_from, name_from, identifier_to, name_to ) ]
        
        connection.callRemote( HydrusServerAMP.IMMessageServer, identifier_to = identifier_to, name_to = name_to, message = message )
        
        # if it breaks, we should pubsub that it broke
        
    
    def StartTalking( self, identifier_from, name_from, identifier_to, name_to ):
        
        # currently on wx loop
        # move it to the twisted loop
        
        # fetch host and port for that id
        
        creator = ClientCreator( reactor, HydrusServerAMP.MessagingClientProtocol )
        
        deferred = creator.connectTCP( host, port )
        
        # deferred is called with the connection, or an error
        # callRemote to register identifier_from and name_from as temp login
        # then add to temp_connections
        
        self._temporary_connections[ ( identifier_from, name_from, identifier_to, name_to ) ] = connection
        
        message = '' # this is just to get the OTR handshake going; it'll never be sent
        
        connection.callRemote( HydrusServerAMP.IMMessageServer, identifier_to = identifier_to, name_to = name_to, message = message )
        
        # how do I detect when we are ready to do encrypted comms?
        # I can check periodically context.status, but that is a _little_ bleh
        # I can write a pubsub in the setStatus thing in context
        # check that article again, or the code, on the exact name
        
        # do a pubsub to say we are ready to do encrypted comms
        
        # if it fails, we should pubsub that it broke
        
    
    def StopTalking( self, identifier, name ):
        
        # close temp connection
        # 
        
        pass
        
    
class IMMessage( HydrusData.HydrusYAMLBase ):
    
    yaml_tag = u'!IMMessage'
    
class IMMessageQuestion( IMMessage ):
    
    yaml_tag = u'!IMMessageQuestion'
    
    def __init__( self, job_key = None ):
        
        if job_key is None: job_key = HydrusData.GenerateKey()
        
        self._job_key = job_key
        
    
    def GenerateAnswer( self, answer ):
        
        return IMMessageQuestionAnswer( self._job_key, answer )
        
    
    def GetJobKey( self ): return self._job_key
    
class IMMessageQuestionAnswer( IMMessageQuestion ):
    
    yaml_tag = u'!IMMessageQuestionAnswer'
    
    def __init__( self, job_key, answer ):
        
        IMMessageQuestion.__init__( self, job_key )
        
        self._answer = answer
        
    
    def GetAnswer( self ): return self._answer
    
class IMMessageQuestionFiles( IMMessageQuestion ):
    
    yaml_tag = u'!IMMessageFiles'
    
    def __init__( self, media_results ):
        
        IMMessageQuestion.__init__( self )
        
        self._text = text
        
    
IM_MESSAGE_TYPE_CONVO = 0
IM_MESSAGE_TYPE_STATUS = 1

class IMMessageText( IMMessage ):
    
    yaml_tag = u'!IMMessageText'
    
    def __init__( self, message_type, text ):
        
        self._type = message_type
        self._text = text
        
    
    def ToTuple( self ): return ( self._type, self._text )
    '''