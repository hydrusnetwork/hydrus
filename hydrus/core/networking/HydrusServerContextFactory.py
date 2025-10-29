from hydrus.core import HydrusGlobals as HG

from OpenSSL import crypto

def load_certs_ordered( pem_bytes: bytes ) -> list[ crypto.X509 ]:
    """
    Parse all PEM certs and return them ordered as [leaf, intermediates...].
    Works even if the input PEMs are in arbitrary order.
    """
    
    blocks = []
    
    for chunk in pem_bytes.split( b"-----END CERTIFICATE-----" ):
        
        if b"-----BEGIN CERTIFICATE-----" in chunk:
            
            blocks.append( chunk + b"-----END CERTIFICATE-----" )
            
        
    
    certs = [ crypto.load_certificate( crypto.FILETYPE_PEM, b ) for b in blocks ]
    
    # Map subjects and issuers to chain them.
    by_subject: dict[ bytes, crypto.X509 ] = { c.get_subject().der(): c for c in certs }
    issuers = { c.get_issuer().der() for c in certs }
    
    # Leaf: subject that is not any other cert’s issuer (or self-signed if only one)
    leaf = None
    
    for c in certs:
        
        if c.get_subject().der() not in issuers:
            
            leaf = c
            
            break
            
        
    
    if leaf is None:
        
        # All issuers match some subject -> probably a self-signed single cert
        # or weird bundle. Fallback to first.
        leaf = certs[0]
        
    
    # Walk issuer links to build the chain
    ordered = [leaf]
    current = leaf
    
    while True:
        
        issuer_der = current.get_issuer().der()
        
        if issuer_der == current.get_subject().der():
            
            # self-signed root (don’t send roots)
            break
            
        
        nxt = by_subject.get( issuer_der )
        
        if nxt is None:
            
            break
            
        
        # Stop before adding a root if present
        if nxt.get_subject().der() == nxt.get_issuer().der():
            
            break
            
        
        ordered.append( nxt )
        current = nxt
        
    
    return ordered
    

def GenerateSSLContextFactory( ssl_cert_path, ssl_key_path ):
    
    if HG.twisted_is_broke:
        
        raise Exception( 'Twisted is not available!' )
        
    
    import twisted.internet.ssl
    
    with open( ssl_cert_path, "rb" ) as f:
        
        fullchain_pem = f.read()
        
    
    certs = load_certs_ordered( fullchain_pem )
    
    leaf = certs[0]
    
    chain = certs[1:] # empty list for self-signed, that's ok
    
    with open( ssl_key_path, "rb" ) as f:
        
        key = crypto.load_privatekey( crypto.FILETYPE_PEM, f.read() )
        
    
    context_factory = twisted.internet.ssl.CertificateOptions(
        privateKey=key,
        certificate=leaf,
        extraCertChain=chain,
        raiseMinimumTo=twisted.internet.ssl.TLSVersion.TLSv1_2,
    )
    
    return context_factory
    
    # this is the old method; it is only appropriate for self-signed certs since the defaultcontextfactory only loads the first cert in cert_path; it doesn't load up the chain
    '''
    ( ssl_cert_path, ssl_key_path ) = self.db.GetSSLPaths()
    
    sslmethod = twisted.internet.ssl.SSL.TLSv1_2_METHOD
    
    context_factory = twisted.internet.ssl.DefaultOpenSSLContextFactory( ssl_key_path, ssl_cert_path, sslmethod )
    '''
    
