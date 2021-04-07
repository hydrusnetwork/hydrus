import random
import unittest

from hydrus.core import HydrusExceptions
from hydrus.core.networking import HydrusNATPunch

TEST_EXTERNAL_IP = '1.2.3.4'
TEST_ROUTER_ADDRESS = '192.168.0.1'
TEST_ME_IP = '192.168.0.101'
TEST_QUAKE_SERVER_IP = '192.168.0.102'

GET_MAPPINGS_OK = '''upnpc : miniupnpc library test client, version 1.9.
 (c) 2005-2014 Thomas Bernard.
Go to http://miniupnp.free.fr/ or http://miniupnp.tuxfamily.org/
for more information.
List of UPNP devices found on the network :
 desc: http://192.168.0.1/root.sxml
 st: urn:schemas-upnp-org:device:InternetGatewayDevice:1

Found valid IGD : http://192.168.0.1:4444/wipconn
Local LAN ip address : 192.168.0.101
Connection Type : IP_Routed
Status : Connected, uptime=123456s, LastConnectionError : ERROR_NONE
  Time started : Thu Oct 01 12:13:14 2020
MaxBitRateDown : 1000000000 bps (1000.0 Mbps)   MaxBitRateUp 1000000000 bps (1000.0 Mbps)
ExternalIPAddress = 1.2.3.4
 i protocol exPort->inAddr:inPort description remoteHost leaseTime
 0 TCP 45871->192.168.0.101:45871 'Hydrus Client API' '' 0
 1 UDP 44040->192.168.0.101:44040 'xXxP2P_LiNuX_ISO_420xXx' '' 3600
 2 TCP  1240->192.168.0.102:980  'Quake' '' 0
GetGenericPortMappingEntry() returned 713 (SpecifiedArrayIndexInvalid)'''

ADD_STDOUT_OK = '''upnpc : miniupnpc library test client, version 1.9.
 (c) 2005-2014 Thomas Bernard.
Go to http://miniupnp.free.fr/ or http://miniupnp.tuxfamily.org/
for more information.
List of UPNP devices found on the network :
 desc: http://192.168.0.1/root.sxml
 st: urn:schemas-upnp-org:device:InternetGatewayDevice:1

Found valid IGD : http://192.168.0.1:4444/wipconn
Local LAN ip address : 192.168.0.101
ExternalIPAddress = 1.2.3.4
InternalIP:Port = 192.168.0.101:45871
external 1.2.3.4:45871 TCP is redirected to internal 192.168.0.101:45871 (duration=0)'''

ADD_STDOUT_PORT_MAPPED_OTHER_PORT = '''upnpc : miniupnpc library test client, version 1.9.
 (c) 2005-2014 Thomas Bernard.
Go to http://miniupnp.free.fr/ or http://miniupnp.tuxfamily.org/
for more information.
List of UPNP devices found on the network :
 desc: http://192.168.0.1/root.sxml
 st: urn:schemas-upnp-org:device:InternetGatewayDevice:1

Found valid IGD : http://192.168.0.1:4444/wipconn
Local LAN ip address : 192.168.0.101
ExternalIPAddress = 1.2.3.4
AddPortMapping(45871, 4000, 192.168.0.101) failed with code 718 (ConflictInMappingEntry)
InternalIP:Port = 192.168.0.101:45871
external 1.2.3.4:45871 TCP is redirected to internal 192.168.0.101:45871 (duration=0)'''

ADD_STDOUT_PORT_MAPPED_OTHER_COMP = '''upnpc : miniupnpc library test client, version 1.9.
 (c) 2005-2014 Thomas Bernard.
Go to http://miniupnp.free.fr/ or http://miniupnp.tuxfamily.org/
for more information.
List of UPNP devices found on the network :
 desc: http://192.168.0.1/root.sxml
 st: urn:schemas-upnp-org:device:InternetGatewayDevice:1

Found valid IGD : http://192.168.0.1:4444/wipconn
Local LAN ip address : 192.168.0.101
ExternalIPAddress = 1.2.3.4
AddPortMapping(45871, 45871, 192.168.0.101) failed with code 718 (ConflictInMappingEntry)
InternalIP:Port = 192.168.0.102:45871
external 1.2.3.4:45871 TCP is redirected to internal 192.168.0.102:45871 (duration=0)'''

class TestNATPunch( unittest.TestCase ):
    
    def test_upnp_parsing( self ):
        
        mappings = HydrusNATPunch.GetUPnPMappingsParseResponse( GET_MAPPINGS_OK )
        
        expected_mappings = {
            ( 'Hydrus Client API', '192.168.0.101', 45871, 45871, 'TCP', 0 ),
            ( 'xXxP2P_LiNuX_ISO_420xXx', '192.168.0.101', 44040, 44040, 'UDP', 3600 ),
            ( 'Quake', '192.168.0.102', 980, 1240, 'TCP', 0 )
        }
        
        self.assertEqual( expected_mappings, set( mappings ) )
        
        #
        
        HydrusNATPunch.AddUPnPMappingCheckResponse( TEST_ME_IP, 45871, 45871, 'TCP', ADD_STDOUT_OK, '' )
        
        try:
            
            HydrusNATPunch.AddUPnPMappingCheckResponse( TEST_ME_IP, 4000, 45871, 'TCP', ADD_STDOUT_PORT_MAPPED_OTHER_PORT, '' )
            
        except HydrusExceptions.RouterException as e:
            
            self.assertIn( 'The UPnP mapping of 192.168.0.101:4000->external:45871(TCP) could not be added because that external port is already forwarded to another port on this computer!', str( e ) )
            
        
        try:
            
            HydrusNATPunch.AddUPnPMappingCheckResponse( TEST_ME_IP, 45871, 45871, 'TCP', ADD_STDOUT_PORT_MAPPED_OTHER_COMP, '' )
            
        except HydrusExceptions.RouterException as e:
            
            self.assertIn( 'The UPnP mapping of 192.168.0.101:45871->external:45871(TCP) could not be added because that external port is already mapped to another computer on this network!', str( e ) )
            
        
    
