import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client.metadata import ClientTags

class TestHydrusData( unittest.TestCase ):
    
    def test_ordinals( self ):
        
        self.assertEqual( HydrusData.ConvertIntToPrettyOrdinalString( 1 ), '1st' )
        self.assertEqual( HydrusData.ConvertIntToPrettyOrdinalString( 2 ), '2nd' )
        self.assertEqual( HydrusData.ConvertIntToPrettyOrdinalString( 3 ), '3rd' )
        self.assertEqual( HydrusData.ConvertIntToPrettyOrdinalString( 4 ), '4th' )
        
        self.assertEqual( HydrusData.ConvertIntToPrettyOrdinalString( 11 ), '11th' )
        self.assertEqual( HydrusData.ConvertIntToPrettyOrdinalString( 12 ), '12th' )
        
        self.assertEqual( HydrusData.ConvertIntToPrettyOrdinalString( 213 ), '213th' )
        
        self.assertEqual( HydrusData.ConvertIntToPrettyOrdinalString( 1011 ), '1,011th' )
        
    
