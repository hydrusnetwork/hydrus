import unittest

from hydrus.core import HydrusNumbers

class TestHydrusData( unittest.TestCase ):
    
    def test_ordinals( self ):
        
        self.assertEqual( HydrusNumbers.ConvertIntToPrettyOrdinalString( 1 ), '1st' )
        self.assertEqual( HydrusNumbers.ConvertIntToPrettyOrdinalString( 2 ), '2nd' )
        self.assertEqual( HydrusNumbers.ConvertIntToPrettyOrdinalString( 3 ), '3rd' )
        self.assertEqual( HydrusNumbers.ConvertIntToPrettyOrdinalString( 4 ), '4th' )
        
        self.assertEqual( HydrusNumbers.ConvertIntToPrettyOrdinalString( 11 ), '11th' )
        self.assertEqual( HydrusNumbers.ConvertIntToPrettyOrdinalString( 12 ), '12th' )
        
        self.assertEqual( HydrusNumbers.ConvertIntToPrettyOrdinalString( 213 ), '213th' )
        
        self.assertEqual( HydrusNumbers.ConvertIntToPrettyOrdinalString( 1011 ), '1,011th' )
        
    
