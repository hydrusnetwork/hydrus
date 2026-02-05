import datetime
import os
import stat

from hydrus.core import HydrusDateTime

try:
    
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    
    CRYPTO_OK = True
    
except Exception as e:
    
    CRYPTO_OK = False
    

try:
    
    import OpenSSL
    
    OPENSSL_OK = True
    
except Exception as e:
    
    OPENSSL_OK = False
    

def GenerateOpenSSLCertAndKeyFile( cert_path, key_path ):
    
    if not CRYPTO_OK:
        
        raise Exception( 'Sorry, to make your own cert, you need "cryptography" library! You should be able to get it with pip.' )
        
    
    # cribbed from here https://cryptography.io/en/latest/x509/tutorial/#creating-a-self-signed-certificate
    
    # private key
    key = rsa.generate_private_key( public_exponent = 65537, key_size = 2048 )
    
    # create a self-signed cert
    
    subject = issuer = x509.Name(
        [
        x509.NameAttribute( NameOID.COUNTRY_NAME, 'HN' ),
        x509.NameAttribute( NameOID.ORGANIZATION_NAME, 'hydrus network' ),
        x509.NameAttribute( NameOID.ORGANIZATIONAL_UNIT_NAME, os.urandom( 32 ).hex() )
        ]
    )
    
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        HydrusDateTime.nowutc()
    ).not_valid_after(
        HydrusDateTime.nowutc() + datetime.timedelta( days = 365 * 10 )
    ).add_extension(
        x509.SubjectAlternativeName( [ x509.DNSName( 'localhost' ) ] ),
        critical = False
    ).sign( key, hashes.SHA256() )
    
    cert_bytes = cert.public_bytes( serialization.Encoding.PEM )
    
    with open( cert_path, 'wb' ) as f:
        
        f.write( cert_bytes )
        
    
    os.chmod( cert_path, stat.S_IREAD )
    
    # no pass, we are full jej mode here for ease (it wants the pass prompt on service startup)
    # encryption_algorithm = serialization.BestAvailableEncryption( b"passphrase" )
    
    key_bytes = key.private_bytes(
        encoding = serialization.Encoding.PEM,
        format = serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm = serialization.NoEncryption()
    )
    
    with open( key_path, 'wb' ) as f:
        
        f.write( key_bytes )
        
    
    os.chmod( key_path, stat.S_IREAD )
    
'''
# old crypto code experiments

import Crypto.Cipher.AES
import Crypto.Cipher.PKCS1_OAEP
import Crypto.PublicKey.RSA

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
    
'''
