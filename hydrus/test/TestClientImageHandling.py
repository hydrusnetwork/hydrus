import os
import unittest

from hydrus.core import HydrusConstants as HC

from hydrus.client import ClientConstants as CC
from hydrus.client.files.images import ClientImagePerceptualHashes

class TestImageHandling( unittest.TestCase ):
    
    def test_perceptual_hash( self ):
        
        perceptual_hashes = ClientImagePerceptualHashes.GenerateShapePerceptualHashes( os.path.join( HC.STATIC_DIR, 'hydrus.png' ), HC.IMAGE_PNG )
        
        self.assertEqual( perceptual_hashes, set( [ b'\xb4M\xc7\xb2M\xcb8\x1c' ] ) )
        
        perceptual_hashes = ClientImagePerceptualHashes.DiscardBlankPerceptualHashes( { CC.BLANK_PERCEPTUAL_HASH } )
        
        self.assertEqual( perceptual_hashes, set() )
        
        perceptual_hashes = ClientImagePerceptualHashes.DiscardBlankPerceptualHashes( { b'\xb4M\xc7\xb2M\xcb8\x1c', CC.BLANK_PERCEPTUAL_HASH } )
        
        self.assertEqual( perceptual_hashes, set( [ b'\xb4M\xc7\xb2M\xcb8\x1c' ] ) )
        
    
