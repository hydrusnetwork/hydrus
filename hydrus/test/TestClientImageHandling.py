import os
import unittest

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientImageHandling

class TestImageHandling( unittest.TestCase ):
    
    def test_phash( self ):
        
        phashes = ClientImageHandling.GenerateShapePerceptualHashes( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), HC.IMAGE_PNG )
        
        self.assertEqual( phashes, set( [ b'\xb4M\xc7\xb2M\xcb8\x1c' ] ) )
        
        phashes = ClientImageHandling.DiscardBlankPerceptualHashes( { CC.BLANK_PHASH } )
        
        self.assertEqual( phashes, set() )
        
        phashes = ClientImageHandling.DiscardBlankPerceptualHashes( { b'\xb4M\xc7\xb2M\xcb8\x1c', CC.BLANK_PHASH } )
        
        self.assertEqual( phashes, set( [ b'\xb4M\xc7\xb2M\xcb8\x1c' ] ) )
        
