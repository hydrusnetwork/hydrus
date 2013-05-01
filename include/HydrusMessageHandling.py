import Crypto.Hash.SHA256
import Crypto.Signature.PKCS1_v1_5
import hashlib
import HydrusConstants as HC
import HydrusEncryption
import os
import time
import traceback
import wx
import yaml
import zlib

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
    
class Message( HC.HydrusYAMLBase ):
    
    yaml_tag = u'!Message'
    
    def __init__( self, conversation_key, contact_from, contacts_to, subject, body, timestamp, files = [], private_key = None ):
        
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
        
        message += ''.join( [ yaml.safe_dump( public_key ) for public_key in contact_to_public_keys ] ) + subject_text + body_text + ''.join( self._files ) + str( self._conversation_key ) + str( self._timestamp )
        
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
        
    