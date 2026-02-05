import os
import shutil
import socket
import threading
import traceback

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusText
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusSubprocess

# TODO: unwind all this, the notes about upnpc, all that. it is obsolete

# the _win32, _linux, _osx stuff here is legacy, from when I used to bundle these exes. this cause anti-virus false positive wew

if HC.PLATFORM_WINDOWS:
    
    possible_bin_filenames = [ 'upnpc.exe', 'upnpc-static.exe', 'miniupnpc.exe', 'upnpc_win32.exe' ]
    
else:
    
    possible_bin_filenames = [ 'upnpc', 'upnpc-static', 'upnpc-shared', 'miniupnpc' ]
    
    if HC.PLATFORM_LINUX:
        
        possible_bin_filenames.append( 'upnpc_linux' )
        
    elif HC.PLATFORM_MACOS:
        
        possible_bin_filenames.append( 'upnpc_osx' )
        
    
UPNPC_PATH = None

UPNPC_MANAGER_ERROR_PRINTED = False
UPNPC_MISSING_ERROR_PRINTED = False

for filename in possible_bin_filenames:
    
    possible_path = os.path.join( HC.BIN_DIR, filename )
    
    if os.path.exists( possible_path ):
        
        UPNPC_PATH = possible_path
        
        break
        
    
    possible_path_which = shutil.which( filename )
    
    if possible_path_which is not None:
        
        UPNPC_PATH = possible_path_which
        
        break
        
    
EXTERNAL_IP = {}
EXTERNAL_IP[ 'ip' ] = None
EXTERNAL_IP[ 'time' ] = 0

UPNPC_IS_MISSING = UPNPC_PATH is None

def RaiseMissingUPnPcError( operation ):
    
    message = 'Unfortunately, the operation "{}" requires miniupnpc, which does not seem to be available for your system. You can install it yourself easily, please check install_dir/bin/upnpc_readme.txt for more information!'.format( operation )
    
    global UPNPC_MISSING_ERROR_PRINTED
    
    if not UPNPC_MISSING_ERROR_PRINTED:
        
        HydrusData.ShowText( message )
        
        UPNPC_MISSING_ERROR_PRINTED = True
        
    
    raise FileNotFoundError( message )
    
def GetExternalIP():
    
    if UPNPC_IS_MISSING:
        
        RaiseMissingUPnPcError( 'fetch external IP' )
        
    
    if HydrusTime.TimeHasPassed( EXTERNAL_IP[ 'time' ] + ( 3600 * 24 ) ):
        
        cmd = [ UPNPC_PATH, '-l' ]
        
        HydrusData.CheckProgramIsNotShuttingDown()
        
        try:
            
            ( stdout, stderr ) = HydrusSubprocess.RunSubprocess( cmd, timeout = 30 )
            
        except FileNotFoundError:
            
            RaiseMissingUPnPcError( 'fetch external IP' )
            
        
        if stderr is not None and len( stderr ) > 0:
            
            raise Exception( 'Problem while trying to fetch External IP (if it says No IGD UPnP Device, you are either on a VPN or your router does not seem to support UPnP):' + '\n' * 2 + str( stderr ) )
            
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
            EXTERNAL_IP[ 'time' ] = HydrusTime.GetNow()
            
        
    
    return EXTERNAL_IP[ 'ip' ]
    
def GetLocalIP():
    
    return socket.gethostbyname( socket.gethostname() )
    
def AddUPnPMapping( internal_client, internal_port, external_port, protocol, description, duration = 3600 ):
    
    if UPNPC_IS_MISSING:
        
        RaiseMissingUPnPcError( 'add UPnP port forward' )
        
    
    cmd = [ UPNPC_PATH, '-e', description, '-a', internal_client, str( internal_port ), str( external_port ), protocol, str( duration ) ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        ( stdout, stderr ) = HydrusSubprocess.RunSubprocess( cmd, timeout = 30 )
        
    except FileNotFoundError:
        
        RaiseMissingUPnPcError( 'add UPnP port forward' )
        
    
    AddUPnPMappingCheckResponse( internal_client, internal_port, external_port, protocol, stdout, stderr )
    
def AddUPnPMappingCheckResponse( internal_client, internal_port, external_port, protocol, stdout, stderr ):
    
    if stdout is not None and 'failed with code' in stdout:
        
        already_exists_str = '{} TCP is redirected to internal {}:{}'.format( external_port, internal_client, internal_port )
        wrong_port_str = '{} TCP is redirected to internal {}'.format( external_port, internal_client )
        points_elsewhere_str = '{} TCP is redirected to internal '.format( external_port )
        
        if already_exists_str in stdout:
            
            raise HydrusExceptions.RouterException( 'The UPnP mapping of {}:{}->external:{}({}) already exists, and your router did not like it being re-added! It is probably a good idea to set this manually through your router interface with an indefinite lease.'.format( internal_client, internal_port, external_port, protocol ) )
            
        elif wrong_port_str in stdout:
            
            raise HydrusExceptions.RouterException( 'The UPnP mapping of {}:{}->external:{}({}) could not be added because that external port is already forwarded to another port on this computer! You will have to remove it, either through hydrus or the router\'s direct interface (probably a web server hosted at its address).'.format( internal_client, internal_port, external_port, protocol ) )
            
        elif points_elsewhere_str in stdout:
            
            raise HydrusExceptions.RouterException( 'The UPnP mapping of {}:{}->external:{}({}) could not be added because that external port is already mapped to another computer on this network! You will have to remove it, either through hydrus or the router\'s direct interface (probably a web server hosted at its address).'.format( internal_client, internal_port, external_port, protocol ) )
            
        
        if 'UnknownError' in stdout:
            
            raise HydrusExceptions.RouterException( 'Problem while trying to add UPnP mapping:' + '\n' * 2 + stdout )
            
        else:
            
            raise Exception( 'Problem while trying to add UPnP mapping:' + '\n' * 2 + stdout )
            
        
    
    if stderr is not None and len( stderr ) > 0:
        
        raise Exception( 'Problem while trying to add UPnP mapping:' + '\n' * 2 + stderr )
        
    
def GetUPnPMappings():
    
    if UPNPC_IS_MISSING:
        
        RaiseMissingUPnPcError( 'get current UPnP port forward mappings' )
        
    
    cmd = [ UPNPC_PATH, '-l' ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        ( stdout, stderr ) = HydrusSubprocess.RunSubprocess( cmd, timeout = 30 )
        
    except FileNotFoundError:
        
        RaiseMissingUPnPcError( 'get current UPnP port forward mappings' )
        
    
    if stderr is not None and len( stderr ) > 0:
        
        raise Exception( 'Problem while trying to fetch UPnP mappings (if it says No IGD UPnP Device, you are either on a VPN or your router does not seem to support UPnP):' + '\n' * 2 + stderr )
        
    else:
        
        return GetUPnPMappingsParseResponse( stdout )
        
    
def GetUPnPMappingsParseResponse( stdout ):
    
    try:
        
        lines = HydrusText.DeserialiseNewlinedTexts( stdout )
        
        i = lines.index( 'i protocol exPort->inAddr:inPort description remoteHost leaseTime' )
        
        data_lines = []
        
        i += 1
        
        while i < len( lines ):
            
            if lines[ i ][0] not in ( ' ', '0', '1', '2', '3', '4', '5', '6', '7', '8', '9' ): break
            
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
        
        raise Exception( 'Problem while trying to parse UPnP mappings:' + '\n' * 2 + str( e ) )
        
    
def RemoveUPnPMapping( external_port, protocol ):
    
    if UPNPC_IS_MISSING:
        
        RaiseMissingUPnPcError( 'remove UPnP port forward' )
        
    
    cmd = [ UPNPC_PATH, '-d', str( external_port ), protocol ]
    
    HydrusData.CheckProgramIsNotShuttingDown()
    
    try:
        
        ( stdout, stderr ) = HydrusSubprocess.RunSubprocess( cmd, timeout = 30 )
        
    except FileNotFoundError:
        
        RaiseMissingUPnPcError( 'remove UPnP port forward' )
        
    
    if stderr is not None and len( stderr ) > 0:
        
        raise Exception( 'Problem while trying to remove UPnP mapping:' + '\n' * 2 + stderr )
        
    
class ServicesUPnPManager( object ):
    
    def __init__( self, services ):
        
        self._lock = threading.Lock()
        
        self._services = services
        
    
    def _RefreshUPnP( self, force_wipe = False ):
        
        running_service_with_upnp = True in ( service.GetPort() is not None and service.GetUPnPPort() is not None for service in self._services )
        
        if not force_wipe:
            
            if not running_service_with_upnp:
                
                return
                
            
        
        if running_service_with_upnp and UPNPC_IS_MISSING:
            
            return # welp
            
        
        try:
            
            local_ip = GetLocalIP()
            
        except Exception as e:
            
            return # can't get local IP, we are wewlad atm, probably some complicated multiple network situation we'll have to deal with later
            
        
        try:
            
            current_mappings = GetUPnPMappings()
            
        except FileNotFoundError:
            
            if not force_wipe:
                
                global UPNPC_MANAGER_ERROR_PRINTED
                
                if not UPNPC_MANAGER_ERROR_PRINTED:
                    
                    HydrusData.ShowText( 'Hydrus was set up to manage your services\' port forwards with UPnP, but the miniupnpc executable is not available. Please check install_dir/bin/upnpc_readme.txt for more details.' )
                    
                    UPNPC_MANAGER_ERROR_PRINTED = True
                    
                
            
            return # in this case, most likely miniupnpc could not be found, so skip for now
            
        except Exception as e:
            
            return # This IGD probably doesn't support UPnP, so don't spam the user with errors they can't fix!
            
        
        our_mappings = { ( internal_client, internal_port ) : external_port for ( description, internal_client, internal_port, external_port, protocol, enabled ) in current_mappings }
        
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
                    
                except HydrusExceptions.RouterException:
                    
                    HydrusData.Print( 'The UPnP Daemon tried to add {}:{}->external:{} but it failed. Please try it manually to get a full log of what happened.'.format( local_ip, internal_port, upnp_port ) )
                    
                    return
                    
                
            
        
    
    def SetServices( self, services ):
        
        with self._lock:
            
            self._services = services
            
            self._RefreshUPnP()
            
        
    
    def RefreshUPnP( self ):
        
        with self._lock:
            
            self._RefreshUPnP()
            
        
    
