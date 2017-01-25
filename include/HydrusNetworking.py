import httplib
import socket
import ssl

def GetLocalConnection( port, https = False ):
    
    old_socket = httplib.socket.socket
    
    httplib.socket.socket = socket._socketobject
    
    try:
        
        if https:
            
            context = ssl.SSLContext( ssl.PROTOCOL_SSLv23 )
            context.options |= ssl.OP_NO_SSLv2
            context.options |= ssl.OP_NO_SSLv3
            
            connection = httplib.HTTPSConnection( '127.0.0.1', port, timeout = 8, context = context )
            
        else:
            
            connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 8 )
            
        
        connection.connect()
        
    finally:
        
        httplib.socket.socket = old_socket
        
    
    return connection
    
