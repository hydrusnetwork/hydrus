import os
import win32com.client

def GetUPnPMappings():
    
    try:
        
        dispatcher = win32com.client.Dispatch( 'HNetCfg.NATUPnP' )
        
        static_port_mappings = dispatcher.StaticPortMappingCollection
        
    except: raise Exception( 'Could not fetch UPnP Manager!' )
    
    if static_port_mappings is None: raise Exception( 'Could not fetch UPnP info!' + os.linesep + 'Make sure UPnP is enabled for your computer and router, or try restarting your router.' )
    
    mappings = []
    
    for i in range( len( static_port_mappings ) ):
        
        static_port_mapping = static_port_mappings[i]
        
        description = static_port_mapping.Description
        
        internal_client = static_port_mapping.InternalClient
        internal_port = static_port_mapping.InternalPort
        
        external_ip_address = static_port_mapping.ExternalIPAddress
        external_port = static_port_mapping.ExternalPort
        
        protocol = static_port_mapping.Protocol
        
        enabled = static_port_mapping.Enabled
        
        mappings.append( ( description, internal_client, internal_port, external_ip_address, external_port, protocol, enabled ) )
        
    
    return mappings
    
# mappings.Add( external_port,'TCP', internal_port, internal_client, enabled true/false, description )
# socket.gethostbyname( socket.gethostname() )