import HydrusConstants as HC
import os
import socket

if HC.PLATFORM_WINDOWS: import win32com.client

def GetLocalIP(): return socket.gethostbyname( socket.gethostname() )

def GetStaticPortMappingCollection():
    
    try:
        
        dispatcher = win32com.client.Dispatch( 'HNetCfg.NATUPnP' )
        
        static_port_mappings = dispatcher.StaticPortMappingCollection
        
    except: raise Exception( 'Could not fetch UPnP Manager!' )
    
    if static_port_mappings is None: raise Exception( 'Could not fetch UPnP info!' + os.linesep + 'Make sure UPnP is enabled for your computer and router, or try restarting your router.' )
    
    return static_port_mappings
    
def GetUPnPMappings():
    
    static_port_mappings = GetStaticPortMappingCollection()
    
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
    
def AddUPnPMapping( external_port, protocol, internal_port, description ):
    
    internal_client = GetLocalIP()
    
    enabled = True
    
    static_port_mappings = GetStaticPortMappingCollection()
    
    try: static_port_mappings.Add( external_port, protocol, internal_port, internal_client, enabled, description )
    except: raise Exception( 'Attempt to add a UPnP mapping failed; that mapping probably already exists as a UPnP mapping or static port forward already.' )
    
def RemoveUPnPMapping( external_port, protocol ):
    
    static_port_mappings = GetStaticPortMappingCollection()
    
    try: static_port_mappings.Remove( external_port, protocol )
    except: raise Exception( 'Attempt to remove UPnP mapping failed.' )
    