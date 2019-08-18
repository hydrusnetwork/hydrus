from . import ClientConstants as CC
from . import HydrusConstants as HC
from . import HydrusNATPunch
import os
import random
import time
import unittest

class TestNATPunch( unittest.TestCase ):
    
    def test_upnp( self ):
        
        internal_client = HydrusNATPunch.GetLocalIP()
        
        internal_port = random.randint( 1000, 1500 )
        
        external_port = random.randint( 1000, 1500 )
        
        description_tcp = 'hydrus test tcp'
        description_udp = 'hydrus test udp'
        
        HydrusNATPunch.AddUPnPMapping( internal_client, internal_port, external_port, 'TCP', description_tcp )
        HydrusNATPunch.AddUPnPMapping( internal_client, internal_port, external_port, 'UDP', description_udp )
        
        mappings = HydrusNATPunch.GetUPnPMappings()
        
        mappings_without_lease_times = [ mapping[:-1] for mapping in mappings ]
        
        self.assertIn( ( description_tcp, internal_client, internal_port, external_port, 'TCP' ), mappings_without_lease_times )
        self.assertIn( ( description_udp, internal_client, internal_port, external_port, 'UDP' ), mappings_without_lease_times )
        
        HydrusNATPunch.RemoveUPnPMapping( external_port, 'TCP' )
        HydrusNATPunch.RemoveUPnPMapping( external_port, 'UDP' )
        
        mappings = HydrusNATPunch.GetUPnPMappings()
        
        mappings_without_lease_times = [ mapping[:-1] for mapping in mappings ]
        
        self.assertNotIn( ( description_tcp, internal_client, internal_port, external_port, 'TCP' ), mappings_without_lease_times )
        self.assertNotIn( ( description_udp, internal_client, internal_port, external_port, 'UDP' ), mappings_without_lease_times )
        
    
