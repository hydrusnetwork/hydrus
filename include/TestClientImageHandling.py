import ClientImageHandling
import collections
import HydrusConstants as HC
import os
import TestConstants
import unittest

class TestImageHandling( unittest.TestCase ):
    
    def test_phash( self ):
        
        phashes = ClientImageHandling.GenerateShapePerceptualHashes( os.path.join( HC.STATIC_DIR, 'hydrus.png' ) )
        
        self.assertEqual( phashes, set( [ '\xb4M\xc7\xb2M\xcb8\x1c' ] ) )
        
