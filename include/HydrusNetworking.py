import httplib
import socket

def GetLocalConnection( port ):
    
    old_socket = httplib.socket.socket
    
    httplib.socket.socket = socket._socketobject
    
    try:
        
        connection = httplib.HTTPConnection( '127.0.0.1', port, timeout = 8 )
        
        connection.connect()
        
    finally:
        
        httplib.socket.socket = old_socket
        
    
    return connection
    