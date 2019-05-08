from . import ClientConstants as CC
from . import ClientImageHandling
import collections
from . import HydrusConstants as HC
import os
import unittest

class TestImageHandling( unittest.TestCase ):
    
    def test_phash( self ):
        
        phashes = ClientImageHandling.GenerateShapePerceptualHashes( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), HC.IMAGE_PNG )
        
        self.assertEqual( phashes, set( [ b'\xb4M\xc7\xb2M\xcb8\x1c' ] ) )
        
        phashes = ClientImageHandling.DiscardBlankPerceptualHashes( { CC.BLANK_PHASH } )
        
        self.assertEqual( phashes, set() )
        
        phashes = ClientImageHandling.DiscardBlankPerceptualHashes( { b'\xb4M\xc7\xb2M\xcb8\x1c', CC.BLANK_PHASH } )
        
        self.assertEqual( phashes, set( [ b'\xb4M\xc7\xb2M\xcb8\x1c' ] ) )
        
