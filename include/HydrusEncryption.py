import Crypto.Cipher.AES
import Crypto.Cipher.PKCS1_OAEP
import Crypto.PublicKey.RSA
import HydrusConstants as HC
import OpenSSL
import os
import socket
import stat
import traceback

AES_KEY_LENGTH = 32
AES_BLOCK_SIZE = 16

def DecryptAES( aes_key, encrypted_message ):
    
    iv = encrypted_message[:AES_BLOCK_SIZE]
    enciphered_message = encrypted_message[AES_BLOCK_SIZE:]
    
    aes_cipher = Crypto.Cipher.AES.new( aes_key, Crypto.Cipher.AES.MODE_CFB, iv )
    
    padded_message = aes_cipher.decrypt( enciphered_message )
    
    message = UnpadAES( padded_message )
    
    return message
    
def DecryptAESStream( aes_key, stream_in, stream_out ):
    
    iv = stream_in.read( AES_BLOCK_SIZE )
    
    aes_cipher = Crypto.Cipher.AES.new( aes_key, Crypto.Cipher.AES.MODE_CFB, iv )
    
    next_block = stream_in.read( HC.READ_BLOCK_SIZE )
    
    while True:
        
        block = next_block
        
        next_block = stream_in.read( HC.READ_BLOCK_SIZE )
        
        decrypted_block = aes_cipher.decrypt( block )
        
        if next_block == '':
            
            decrypted_block = UnpadAES( decrypted_block )
            
        
        stream_out.write( decrypted_block )
        
        if next_block == '':
            
            break
            
        
    
def DecryptPKCS( private_key, encrypted_message ):
    
    rsa_cipher = Crypto.Cipher.PKCS1_OAEP.new( private_key )
    
    message = rsa_cipher.decrypt( encrypted_message )
    
    return message

def DeserialiseRSAKey( text ):
    
    return Crypto.PublicKey.RSA.importKey( text )
    
def EncryptAES( aes_key, message ):
    
    iv = GenerateIV()
    
    padded_message = PadAES( message )
    
    aes_cipher = Crypto.Cipher.AES.new( aes_key, Crypto.Cipher.AES.MODE_CFB, iv )
    
    enciphered_message = aes_cipher.encrypt( padded_message )
    
    encrypted_message = iv + enciphered_message
    
    return encrypted_message
    
def EncryptAESStream( aes_key, stream_in, stream_out ):
    
    iv = GenerateIV()
    
    stream_out.write( iv )
    
    aes_cipher = Crypto.Cipher.AES.new( aes_key, Crypto.Cipher.AES.MODE_CFB, iv )
    
    next_block = stream_in.read( HC.READ_BLOCK_SIZE )
    
    while True:
        
        block = next_block
        
        next_block = stream_in.read( HC.READ_BLOCK_SIZE )
        
        if next_block == '':
            
            block = PadAES( block )
            
        
        encrypted_block = aes_cipher.encrypt( block )
        
        stream_out.write( encrypted_block )
        
        if next_block == '':
            
            break
            
        
    
def EncryptPKCS( public_key, message ):
    
    rsa_cipher = Crypto.Cipher.PKCS1_OAEP.new( public_key )
    
    # my understanding is that I don't have to manually pad this, cause OAEP does it for me.
    encrypted_message = rsa_cipher.encrypt( message )
    
    return encrypted_message
    
def GenerateAESKey():
    
    return os.urandom( AES_KEY_LENGTH )
    
def GenerateIV():
    
    return os.urandom( AES_BLOCK_SIZE )
    
def GenerateFilteredRandomBytes( byte_to_exclude, num_bytes ):
    
    bytes = []
    
    while len( bytes ) < num_bytes:
        
        new_byte = os.urandom( 1 )
        
        if new_byte != byte_to_exclude:
            
            bytes.append( new_byte )
            
        
    
    return ''.join( bytes )

def GenerateOpenSSLCertAndKeyFile( cert_path, key_path ):
    
    key = OpenSSL.crypto.PKey()
    
    key.generate_key( OpenSSL.crypto.TYPE_RSA, 2048 )
    
    # create a self-signed cert
    cert = OpenSSL.crypto.X509()
    
    cert.get_subject().countryName = 'HN'
    cert.get_subject().organizationName = 'hydrus network'
    cert.get_subject().organizationalUnitName = os.urandom( 32 ).encode( 'hex' )
    cert.set_serial_number( 1 )
    cert.gmtime_adj_notBefore( 0 )
    cert.gmtime_adj_notAfter( 10*365*24*60*60 )
    cert.set_issuer( cert.get_subject() )
    cert.set_pubkey( key )
    cert.sign( key, 'sha256' )
    
    cert_text = OpenSSL.crypto.dump_certificate( OpenSSL.crypto.FILETYPE_PEM, cert )
    
    with open( cert_path, 'wt' ) as f:
        
        f.write( cert_text )
        
    
    os.chmod( cert_path, stat.S_IREAD )
    
    key_text = OpenSSL.crypto.dump_privatekey( OpenSSL.crypto.FILETYPE_PEM, key )
    
    with open( key_path, 'wt' ) as f:
        
        f.write( key_text )
        
    
    os.chmod( key_path, stat.S_IREAD )
    
def GenerateRSAKeyPair():
    
    private_key = Crypto.PublicKey.RSA.generate( 2048 )
    
    public_key = private_key.publickey()
    
    return ( private_key, public_key )
    
def PadAES( message ):
    
    block_size = AES_BLOCK_SIZE
    
    # get last byte
    # add random gumpf (except for last byte), then add last byte again
    
    last_byte = message[-1]
    
    num_bytes_to_add = block_size - ( len( message ) % block_size )
    
    pad = GenerateFilteredRandomBytes( last_byte, num_bytes_to_add - 1 ) + last_byte
    
    return message + pad
    
def SerialiseRSAKey( key ):
    
    return key.exportKey()
    
def UnpadAES( message ):
    
    block_size = AES_BLOCK_SIZE
    
    # check last byte, jump back to previous instance of that byte
    
    last_byte = message[-1]
    
    i = 2
    
    while True:
        
        if message[-i] == last_byte: break
        
        i += 1
        
    
    index_of_correct_end = len( message ) - i
    
    return message[:index_of_correct_end + 1]
    
