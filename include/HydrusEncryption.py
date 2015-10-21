import Crypto.Cipher.AES
import Crypto.Cipher.PKCS1_OAEP
import Crypto.Hash.SHA256
import Crypto.Signature.PKCS1_v1_5
import Crypto.PublicKey.RSA
import hashlib
import HydrusConstants as HC
import HydrusGlobals
import os
import potr
import time
import traceback
import yaml
import zlib
import HydrusGlobals

def AESKeyToText( aes_key, iv ): return ( aes_key + iv ).encode( 'hex' )

def AESTextToKey( text ):
    
    try: keys = text.decode( 'hex' )
    except: raise Exception( 'Could not understand that key!' )
    
    aes_key = keys[:32]
    
    iv = keys[32:]
    
    return ( aes_key, iv )
    
def DecryptAES( aes_key, iv, encrypted_message ):
    
    aes_cipher = Crypto.Cipher.AES.new( aes_key, Crypto.Cipher.AES.MODE_CFB, iv )
    
    padded_message = aes_cipher.decrypt( encrypted_message )
    
    message = UnpadAES( padded_message )
    
    return message
    
def DecryptAESFile( aes_key, iv, path ):
    
    aes_cipher = Crypto.Cipher.AES.new( aes_key, Crypto.Cipher.AES.MODE_CFB, iv )
    
    if '.encrypted' in path: path_to = path.replace( '.encrypted', '' )
    else: path_to = path + '.decrypted'
    
    with open( path, 'rb' ) as encrypted_f:
        
        with open( path_to, 'wb' ) as decrypted_f:
            
            next_block = encrypted_f.read( HC.READ_BLOCK_SIZE )
            
            if next_block.startswith( 'hydrus encrypted zip' ): next_block = next_block.replace( 'hydrus encrypted zip', '', 1 )
            
            while True:
                
                block = next_block
                
                next_block = encrypted_f.read( HC.READ_BLOCK_SIZE )
                
                decrypted_block = aes_cipher.decrypt( block )
                
                if len( next_block ) == 0:
                    
                    decrypted_block = UnpadAES( decrypted_block )
                    
                
                decrypted_f.write( decrypted_block )
                
                if len( next_block ) == 0: break
                
            
        
    
    return path_to
    
def DecryptPKCS( private_key, encrypted_message ):
    
    rsa_cipher = Crypto.Cipher.PKCS1_OAEP.new( private_key )
    
    message = rsa_cipher.decrypt( encrypted_message )
    
    return message
    
def EncryptAES( aes_key, iv, message ):
    
    padded_message = PadAES( message )
    
    aes_cipher = Crypto.Cipher.AES.new( aes_key, Crypto.Cipher.AES.MODE_CFB, iv )
    
    encrypted_message = aes_cipher.encrypt( padded_message )
    
    return encrypted_message
    
def EncryptAESFile( path, preface = '' ):
    
    ( aes_key, iv ) = GenerateAESKeyAndIV()
    
    aes_cipher = Crypto.Cipher.AES.new( aes_key, Crypto.Cipher.AES.MODE_CFB, iv )
    
    with open( path, 'rb' ) as decrypted_f:
        
        with open( path + '.encrypted', 'wb' ) as encrypted_f:
            
            encrypted_f.write( preface )
            
            next_block = decrypted_f.read( HC.READ_BLOCK_SIZE )
            
            while True:
                
                block = next_block
                
                next_block = decrypted_f.read( HC.READ_BLOCK_SIZE )
                
                if len( next_block ) == 0:
                    
                    # block must be the last block
                    
                    block = PadAES( block )
                    
                
                encrypted_block = aes_cipher.encrypt( block )
                
                encrypted_f.write( encrypted_block )
                
                if len( next_block ) == 0: break
                
            
        
    
    aes_key_text = AESKeyToText( aes_key, iv )
    
    with open( path + '.key', 'wb' ) as f: f.write( aes_key_text )
    
def EncryptPKCS( public_key, message ):
    
    rsa_cipher = Crypto.Cipher.PKCS1_OAEP.new( public_key )
    
    # my understanding is that I don't have to manually pad this, cause OAEP does it for me.
    # if that is wrong, then lol
    encrypted_message = rsa_cipher.encrypt( message )
    
    return encrypted_message
    
def GenerateAESKeyAndIV():
    
    aes_key = os.urandom( 32 )
    iv = os.urandom( 16 ) # initialisation vector, aes block_size is 16
    
    return ( aes_key, iv )
    
def GenerateFilteredRandomBytes( byte_to_exclude, num_bytes ):
    
    bytes = []
    
    while len( bytes ) < num_bytes:
        
        new_byte = os.urandom( 1 )
        
        if new_byte != byte_to_exclude: bytes.append( new_byte )
        
    
    return ''.join( bytes )

def GenerateNewPrivateKey(): return Crypto.PublicKey.RSA.generate( 2048 ).exportKey()

def GetPublicKey( private_key_text ):
    
    private_key = TextToKey( private_key_text )
    
    public_key = private_key.publickey()
    
    return public_key.exportKey()
    
def TextToKey( text ): return Crypto.PublicKey.RSA.importKey( text )

def PadAES( message ):
    
    block_size = 16
    
    # get last byte
    # add random gumpf (except for last byte), then add last byte again
    
    last_byte = message[-1]
    
    num_bytes_to_add = block_size - ( len( message ) % block_size )
    
    pad = GenerateFilteredRandomBytes( last_byte, num_bytes_to_add - 1 ) + last_byte
    
    return message + pad
    
def UnpadAES( message ):
    
    block_size = 16
    
    # check last byte, jump back to previous instance of that byte
    
    last_byte = message[-1]
    
    i = 2
    
    while True:
        
        if message[-i] == last_byte: break
        
        i += 1
        
    
    index_of_correct_end = len( message ) - i
    
    return message[:index_of_correct_end + 1]
    
# I based this on the excellent article by Darrik L Mazey, here:
# https://blog.darmasoft.net/2013/06/30/using-pure-python-otr.html

DEFAULT_POLICY_FLAGS = {}

DEFAULT_POLICY_FLAGS[ 'ALLOW_V1' ] = False
DEFAULT_POLICY_FLAGS[ 'ALLOW_V2' ] = True
DEFAULT_POLICY_FLAGS[ 'REQUIRE_ENCRYPTION' ] = True

GenerateOTRKey = potr.compatcrypto.generateDefaultKey
def LoadOTRKey( stream ): return potr.crypt.PK.parsePrivateKey( stream )[0]
def DumpOTRKey( key ): return key.serializePrivateKey()

class HydrusOTRContext( potr.context.Context ):
    
    def getPolicy( self, key ):
        
        if key in DEFAULT_POLICY_FLAGS: return DEFAULT_POLICY_FLAGS[ key ]
        else: return False
        
    
    def inject( self, msg, appdata = None ):
        
        inject_catcher = appdata
        
        inject_catcher.write( msg )
        
    
class HydrusOTRAccount( potr.context.Account ):
    
    def __init__( self, name, privkey, trusts ):
        
        potr.context.Account.__init__( self, name, 'hydrus network otr', 1024, privkey )
        
        self.trusts = trusts
        
    
    def saveTrusts( self ):
        
        HydrusGlobals.controller.Write( 'otr_trusts', self.name, self.trusts )
        
    
    # I need an accounts manager so there is only ever one copy of an account
    # it should fetch name, privkey and trusts from db on bootup
    # savettrusts should just spam to the db because it ain't needed that much.