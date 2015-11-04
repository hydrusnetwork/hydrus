import collections
import HydrusConstants as HC
import HydrusImageHandling
import os
import TestConstants
import unittest

class TestImageHandling( unittest.TestCase ):
    
    def test_phash( self ):
        
        phash = HydrusImageHandling.GeneratePerceptualHash( os.path.join( HC.STATIC_DIR, 'hydrus.png' ) )
        
        self.assertEqual( phash, '\xb0\x08\x83\xb2\x08\x0b8\x08' )
        
