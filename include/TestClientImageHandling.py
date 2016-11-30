import ClientImageHandling
import collections
import HydrusConstants as HC
import os
import TestConstants
import unittest

class TestImageHandling( unittest.TestCase ):
    
    def test_phash( self ):
        
        phashes = ClientImageHandling.GenerateShapePerceptualHashes( os.path.join( HC.STATIC_DIR, 'hydrus.png' ) )
        
        self.assertEqual( phashes, [ '\xb0\x08\x83\xb2\x08\x0b8\x08' ] )
        
