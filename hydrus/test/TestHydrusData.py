import unittest

from hydrus.core import HydrusNumbers

class TestHydrusData( unittest.TestCase ):
    
    def test_ordinals( self ):
        
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 1 ), '1st' )
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 2 ), '2nd' )
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 3 ), '3rd' )
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 4 ), '4th' )
        
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 11 ), '11th' )
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 12 ), '12th' )
        
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 213 ), '213th' )
        
        self.assertEqual( HydrusNumbers.IntToPrettyOrdinalString( 1011 ), '1,011th' )
        
    
