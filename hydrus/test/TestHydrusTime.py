import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusTime

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientData
from hydrus.client.metadata import ClientTags

class TestHydrusTime( unittest.TestCase ):
    
    def test_quick( self ):
        
        self.assertEqual( HydrusTime.TimeDeltaToPrettyTimeDelta( 86400 * 5 ), '5 days' )
        self.assertIn( 'month', HydrusTime.TimeDeltaToPrettyTimeDelta( 86400 * 35 ) )
        self.assertEqual( HydrusTime.TimeDeltaToPrettyTimeDelta( 86400 * 35, no_bigger_than_days = True ), '35 days' )
        
    
