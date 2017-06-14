import HydrusConstants as HC
import HydrusData
import HydrusExceptions
import os
import shlex
import socket
import subprocess
import threading
import traceback

# new stuff starts here

if HC.PLATFORM_LINUX:
    
    upnpc_path = os.path.join( HC.BIN_DIR, 'upnpc_linux' )
    
elif HC.PLATFORM_OSX:
    
    upnpc_path = os.path.join( HC.BIN_DIR, 'upnpc_osx' )
    
elif HC.PLATFORM_WINDOWS:
    
    upnpc_path = os.path.join( HC.BIN_DIR, 'upnpc_win32.exe' )
    

EXTERNAL_IP = {}
EXTERNAL_IP[ 'ip' ] = None
EXTERNAL_IP[ 'time' ] = 0

def GetExternalIP():
    
    if 'external_host' in HC.options and HC.options[ 'external_host' ] is not None:
        
        return HC.options[ 'external_host' ]
        
    
    if HydrusData.TimeHasPassed( EXTERNAL_IP[ 'time' ] + ( 3600 * 24 ) ):
        
        cmd = '"' + upnpc_path + '" -l'
        
        p = subprocess.Popen( shlex.split( cmd ), stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetHideTerminalSubprocessStartupInfo() )
        
        HydrusData.WaitForProcessToFinish( p, 30 )
        
        ( output, error ) = p.communicate()
        
        if error is not None and len( error ) > 0: raise Exception( 'Problem while trying to fetch External IP:' + os.linesep * 2 + HydrusData.ToUnicode( error ) )
        else:
            
            try:
                
                lines = HydrusData.SplitByLinesep( output )
                
                i = lines.index( ' i protocol exPort->inAddr:inPort description remoteHost leaseTime' )
                
                '''ExternalIPAddress = ip'''
                
                ( gumpf, external_ip_address ) = lines[ i - 1 ].split( ' = ' )
                
            except ValueError:
                
                raise Exception( 'Could not parse external IP!' )
                
            
            if external_ip_address == '0.0.0.0':
                
                raise Exception( 'Your UPnP device returned your external IP as 0.0.0.0! Try rebooting it, or overwrite it in options!' )
                
            
            EXTERNAL_IP[ 'ip' ] = external_ip_address
            EXTERNAL_IP[ 'time' ] = HydrusData.GetNow()
            
        
    
    return EXTERNAL_IP[ 'ip' ]
    
def GetLocalIP(): return socket.gethostbyname( socket.gethostname() )

def AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = 3600 ):
    
    cmd = '"' + upnpc_path + '" -e "' + description + '" -a ' + internal_client + ' ' + str( internal_port ) + ' ' + str( external_port ) + ' ' + protocol + ' ' + str( duration )
    
    p = subprocess.Popen( shlex.split( cmd ), stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetHideTerminalSubprocessStartupInfo() )
    
    HydrusData.WaitForProcessToFinish( p, 30 )
    
    ( output, error ) = p.communicate()
    
    if 'x.x.x.x:' + str( external_port ) + ' TCP is redirected to internal ' + internal_client + ':' + str( internal_port ) in output:
        
        raise HydrusExceptions.FirewallException( 'The UPnP mapping of ' + internal_client + ':' + internal_port + '->external:' + external_port + ' already exists as a port forward. If this UPnP mapping is automatic, please disable it.' )
        
    
    if output is not None and 'failed with code' in output:
        
        if 'UnknownError' in output:
            
            raise HydrusExceptions.FirewallException( 'Problem while trying to add UPnP mapping:' + os.linesep * 2 + HydrusData.ToUnicode( output ) )
            
        else:
            
            raise Exception( 'Problem while trying to add UPnP mapping:' + os.linesep * 2 + HydrusData.ToUnicode( output ) )
            
        
    
    if error is not None and len( error ) > 0:
        
        raise Exception( 'Problem while trying to add UPnP mapping:' + os.linesep * 2 + HydrusData.ToUnicode( error ) )
        
    
def GetUPnPMappings():
    
    external_ip_address = GetExternalIP()
    
    cmd = '"' + upnpc_path + '" -l'
    
    p = subprocess.Popen( shlex.split( cmd ), stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetHideTerminalSubprocessStartupInfo() )
    
    HydrusData.WaitForProcessToFinish( p, 30 )
    
    ( output, error ) = p.communicate()
    
    if error is not None and len( error ) > 0:
        
        raise Exception( 'Problem while trying to fetch UPnP mappings:' + os.linesep * 2 + HydrusData.ToUnicode( error ) )
        
    else:
        
        try:
            
            lines = HydrusData.SplitByLinesep( output )
            
            i = lines.index( ' i protocol exPort->inAddr:inPort description remoteHost leaseTime' )
            
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
            
            HydrusData.Print( traceback.format_exc() )
            
            raise Exception( 'Problem while trying to parse UPnP mappings:' + os.linesep * 2 + HydrusData.ToUnicode( e ) )
            
        
    
def RemoveUPnPMapping( external_port, protocol ):
    
    cmd = '"' + upnpc_path + '" -d ' + str( external_port ) + ' ' + protocol
    
    p = subprocess.Popen( shlex.split( cmd ), stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, startupinfo = HydrusData.GetHideTerminalSubprocessStartupInfo() )
    
    HydrusData.WaitForProcessToFinish( p, 30 )
    
    ( output, error ) = p.communicate()
    
    if error is not None and len( error ) > 0: raise Exception( 'Problem while trying to remove UPnP mapping:' + os.linesep * 2 + HydrusData.ToUnicode( error ) )
    
