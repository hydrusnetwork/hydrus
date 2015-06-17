import HydrusConstants as HC
import HydrusExceptions
import os
import socket
import subprocess
import threading
import traceback
from twisted.internet import reactor, defer
from twisted.internet.threads import deferToThread
from twisted.python import log
import HydrusData

# new stuff starts here

if HC.PLATFORM_LINUX: upnpc_path = HC.BIN_DIR + os.path.sep + 'upnpc_linux'
elif HC.PLATFORM_OSX: upnpc_path = HC.BIN_DIR + os.path.sep + 'upnpc_osx'
elif HC.PLATFORM_WINDOWS: upnpc_path = HC.BIN_DIR + os.path.sep + 'upnpc_win32.exe'

EXTERNAL_IP = {}
EXTERNAL_IP[ 'ip' ] = None
EXTERNAL_IP[ 'time' ] = 0

def GetExternalIP():
    
    if HydrusData.GetNow() - EXTERNAL_IP[ 'time' ] > 3600 * 24:
        
        EXTERNAL_IP[ 'time' ] = HydrusData.GetNow()
        
        cmd = [ upnpc_path, ' -l' ]
        
        p = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
        
        p.wait()
        
        ( output, error ) = p.communicate()
        
        if error is not None and len( error ) > 0: raise Exception( 'Problem while trying to fetch External IP:' + os.linesep * 2 + HydrusData.ToString( error ) )
        else:
            
            try:
                
                lines = output.split( os.linesep )
                
                i = lines.index( ' i protocol exPort->inAddr:inPort description remoteHost leaseTime' )
                
                '''ExternalIPAddress = ip'''
                
                ( gumpf, EXTERNAL_IP[ 'ip' ] ) = lines[ i - 1 ].split( ' = ' )
                
            except: raise Exception( 'Problem while trying to fetch External IP.' )
            
        
    
    return EXTERNAL_IP[ 'ip' ]
    
def GetLocalIP(): return socket.gethostbyname( socket.gethostname() )

# old, win32 only stuff

'''

if HC.PLATFORM_WINDOWS: import win32com.client

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
    '''

def AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = 3600 ):
    
    cmd = [ upnpc_path, '-e', description, '-a', internal_client, str( internal_port ), str( external_port ), protocol, str( duration ) ]
    
    p = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
    
    p.wait()
    
    ( output, error ) = p.communicate()
    
    if error is not None and len( error ) > 0: raise Exception( 'Problem while trying to add UPnP mapping:' + os.linesep * 2 + HydrusData.ToString( error ) )
    
def GetUPnPMappings():
    
    cmd = [ upnpc_path, '-l' ]
    
    p = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
    
    p.wait()
    
    ( output, error ) = p.communicate()
    
    if error is not None and len( error ) > 0: raise Exception( 'Problem while trying to fetch UPnP mappings:' + os.linesep * 2 + HydrusData.ToString( error ) )
    else:
        
        try:
            
            lines = output.split( os.linesep )
            
            i = lines.index( ' i protocol exPort->inAddr:inPort description remoteHost leaseTime' )
            
            '''ExternalIPAddress = ip'''
            
            try: ( gumpf, external_ip_address ) = lines[ i - 1 ].split( ' = ' )
            except ValueError: return
            
            data_lines = []
            
            i += 1
            
            while i < len( lines ):
                
                if not lines[ i ][0] in ( ' ', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' ): break
                
                data_lines.append( lines[ i ] )
                
                i += 1
                
            
            processed_data = []
            
            for line in data_lines:
                
                ''' 0 UDP 65533->192.168.0.197:65533 'Skype UDP at 192.168.0.197:65533 (2665)' '' 0'''
                
                while '  ' in line: line = line.replace( '  ', ' ' )
                
                if line.startswith( ' ' ): ( empty, number, protocol, mapping_data, rest_of_line ) = line.split( ' ', 4 )
                else: ( number, protocol, mapping_data, rest_of_line ) = line.split( ' ', 3 )
                
                ( external_port, rest_of_mapping_data ) = mapping_data.split( '->' )
                
                external_port = int( external_port )
                
                ( internal_client, internal_port ) = rest_of_mapping_data.split( ':' )
                
                internal_port = int( internal_port )
                
                ( empty, description, space, remote_host, rest_of_line ) = rest_of_line.split( '\'', 4 )
                
                lease_time = int( rest_of_line[1:] )
                
                processed_data.append( ( description, internal_client, internal_port, external_ip_address, external_port, protocol, lease_time ) )
                
            
            return processed_data
            
        except Exception as e:
            
            print( traceback.format_exc() )
            
            raise Exception( 'Problem while trying to parse UPnP mappings:' + os.linesep * 2 + HydrusData.ToString( e ) )
            
        
    
def RemoveUPnPMapping( external_port, protocol ):
    
    cmd = [ upnpc_path, '-d', str( external_port ), protocol ]
    
    p = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetSubprocessStartupInfo() )
    
    p.wait()
    
    ( output, error ) = p.communicate()
    
    if error is not None and len( error ) > 0: raise Exception( 'Problem while trying to remove UPnP mapping:' + os.linesep * 2 + HydrusData.ToString( error ) )
    