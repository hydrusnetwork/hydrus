from . import ClientImageHandling
import collections
from . import HydrusConstants as HC
import os
import unittest

class TestImageHandling( unittest.TestCase ):
    
    def test_phash( self ):
        
        phashes = ClientImageHandling.GenerateShapePerceptualHashes( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), HC.IMAGE_PNG )
        
        self.assertEqual( phashes, set( [ b'\xb4M\xc7\xb2M\xcb8\x1c' ] ) )
        
