from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusText
import os
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
    
    if HydrusData.TimeHasPassed( EXTERNAL_IP[ 'time' ] + ( 3600 * 24 ) ):
        
        cmd = [ upnpc_path, '-l' ]
        
        sbp_kwargs = HydrusData.GetSubprocessKWArgs( text = True )
        
        p = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
        
        HydrusData.WaitForProcessToFinish( p, 30 )
        
        ( stdout, stderr ) = p.communicate()
        
        if stderr is not None and len( stderr ) > 0:
            
            raise Exception( 'Problem while trying to fetch External IP:' + os.linesep * 2 + str( stderr ) )
            
        else:
            
            try:
                
                lines = HydrusText.DeserialiseNewlinedTexts( stdout )
                
                i = lines.index( 'i protocol exPort->inAddr:inPort description remoteHost leaseTime' )
                
                # ExternalIPAddress = ip
                ( gumpf, external_ip_address ) = lines[ i - 1 ].split( ' = ' )
                
            except ValueError:
                
                raise Exception( 'Could not parse external IP!' )
                
            
            if external_ip_address == '0.0.0.0':
                
                raise Exception( 'Your UPnP device returned your external IP as 0.0.0.0! Try rebooting it, or overwrite it in options!' )
                
            
            EXTERNAL_IP[ 'ip' ] = external_ip_address
            EXTERNAL_IP[ 'time' ] = HydrusData.GetNow()
            
        
    
    return EXTERNAL_IP[ 'ip' ]
    
def GetLocalIP():
    
    return socket.gethostbyname( socket.gethostname() )
    
def AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = 3600 ):
    
    cmd = [ upnpc_path, '-e', description, '-a', internal_client, str( internal_port ), str( external_port ), protocol, str( duration ) ]
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs( text = True )
    
    p = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
    
    HydrusData.WaitForProcessToFinish( p, 30 )
    
    ( stdout, stderr ) = p.communicate()
    
    if 'x.x.x.x:' + str( external_port ) + ' TCP is redirected to internal ' + internal_client + ':' + str( internal_port ) in stdout:
        
        raise HydrusExceptions.FirewallException( 'The UPnP mapping of ' + internal_client + ':' + internal_port + '->external:' + external_port + ' already exists as a port forward. If this UPnP mapping is automatic, please disable it.' )
        
    
    if stdout is not None and 'failed with code' in stdout:
        
        if 'UnknownError' in stdout:
            
            raise HydrusExceptions.FirewallException( 'Problem while trying to add UPnP mapping:' + os.linesep * 2 + stdout )
            
        else:
            
            raise Exception( 'Problem while trying to add UPnP mapping:' + os.linesep * 2 + stdout )
            
        
    
    if stderr is not None and len( stderr ) > 0:
        
        raise Exception( 'Problem while trying to add UPnP mapping:' + os.linesep * 2 + stderr )
        
    
def GetUPnPMappings():
    
    cmd = [ upnpc_path, '-l' ]
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs( text = True )
    
    p = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
    
    HydrusData.WaitForProcessToFinish( p, 30 )
    
    ( stdout, stderr ) = p.communicate()
    
    if stderr is not None and len( stderr ) > 0:
        
        raise Exception( 'Problem while trying to fetch UPnP mappings:' + os.linesep * 2 + stderr )
        
    else:
        
        try:
            
            lines = HydrusText.DeserialiseNewlinedTexts( stdout )
            
            i = lines.index( 'i protocol exPort->inAddr:inPort description remoteHost leaseTime' )
            
            data_lines = []
            
            i += 1
            
            while i < len( lines ):
                
                if not lines[ i ][0] in ( ' ', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' ): break
                
                data_lines.append( lines[ i ] )
                
                i += 1
                
            
            processed_data = []
            
            for line in data_lines:
                
                # 0 UDP 65533->192.168.0.197:65533 'Skype UDP at 192.168.0.197:65533 (2665)' '' 0
                
                while '  ' in line:
                    
                    line = line.replace( '  ', ' ' )
                    
                
                if line.startswith( ' ' ):
                    
                    ( empty, number, protocol, mapping_data, rest_of_line ) = line.split( ' ', 4 )
                    
                else:
                    
                    ( number, protocol, mapping_data, rest_of_line ) = line.split( ' ', 3 )
                    
                
                ( external_port, rest_of_mapping_data ) = mapping_data.split( '->' )
                
                external_port = int( external_port )
                
                if rest_of_mapping_data.count( ':' ) == 1:
                    
                    ( internal_client, internal_port ) = rest_of_mapping_data.split( ':' )
                    
                else:
                    
                    parts = rest_of_mapping_data.split( ':' )
                    
                    internal_port = parts.pop( -1 )
                    
                    internal_client = ':'.join( parts )
                    
                
                internal_port = int( internal_port )
                
                ( empty, description, space, remote_host, rest_of_line ) = rest_of_line.split( '\'', 4 )
                
                lease_time = int( rest_of_line[1:] )
                
                processed_data.append( ( description, internal_client, internal_port, external_port, protocol, lease_time ) )
                
            
            return processed_data
            
        except Exception as e:
            
            HydrusData.Print( 'UPnP problem:' )
            HydrusData.Print( traceback.format_exc() )
            HydrusData.Print( 'Full response follows:' )
            HydrusData.Print( stdout )
            
            raise Exception( 'Problem while trying to parse UPnP mappings:' + os.linesep * 2 + str( e ) )
            
        
    
def RemoveUPnPMapping( external_port, protocol ):
    
    cmd = [ upnpc_path, '-d', str( external_port ), protocol ]
    
    sbp_kwargs = HydrusData.GetSubprocessKWArgs( text = True )
    
    p = subprocess.Popen( cmd, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
    
    HydrusData.WaitForProcessToFinish( p, 30 )
    
    ( stdout, stderr ) = p.communicate()
    
    if stderr is not None and len( stderr ) > 0: raise Exception( 'Problem while trying to remove UPnP mapping:' + os.linesep * 2 + stderr )
    

class ServicesUPnPManager( object ):
    
    def __init__( self, services ):
        
        self._lock = threading.Lock()
        
        self._services = services
        
    
    def _RefreshUPnP( self, force_wipe = False ):
        
        if not force_wipe:
            
            running_service_with_upnp = True in ( service.GetPort() is not None and service.GetUPnPPort() is not None for service in self._services )
            
            if not running_service_with_upnp:
                
                return
                
            
        
        try:
            
            local_ip = GetLocalIP()
            
            current_mappings = GetUPnPMappings()
            
            our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_port, protocol, enabled ) in current_mappings }
            
        except:
            
            return # This IGD probably doesn't support UPnP, so don't spam the user with errors they can't fix!
            
        
        for service in self._services:
            
            internal_port = service.GetPort()
            upnp_port = service.GetUPnPPort()
            
            if ( local_ip, internal_port ) in our_mappings:
                
                current_external_port = our_mappings[ ( local_ip, internal_port ) ]
                
                port_is_incorrect = upnp_port is None or upnp_port != current_external_port
                
                if port_is_incorrect or force_wipe:
                    
                    RemoveUPnPMapping( current_external_port, 'TCP' )
                    
                
            
            
        
        for service in self._services:
            
            internal_port = service.GetPort()
            upnp_port = service.GetUPnPPort()
            
            if upnp_port is not None:
                
                service_type = service.GetServiceType()
                
                protocol = 'TCP'
                
                description = HC.service_string_lookup[ service_type ] + ' at ' + local_ip + ':' + str( internal_port )
                
                duration = 86400
                
                try:
                    
                    AddUPnPMapping( local_ip, internal_port, upnp_port, protocol, description, duration = duration )
                    
                except HydrusExceptions.FirewallException:
                    
                    HydrusData.Print( 'The UPnP Daemon tried to add ' + local_ip + ':' + internal_port + '->external:' + upnp_port + ' but it failed due to router error. Please try it manually to get a full log of what happened.' )
                    
                    return
                    
                
            
        
    
    def SetServices( self, services ):
        
        with self._lock:
            
            self._services = services
            
            self._RefreshUPnP( force_wipe = True )
            
        
    
    def RefreshUPnP( self ):
        
        with self._lock:
            
            self._RefreshUPnP()
            
        
    
