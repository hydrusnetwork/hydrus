import TestConstants
import unittest

class TestDB( unittest.TestCase ): pass
    
if __name__ == '__main__':
    
    app = TestConstants.TestController()
    
    unittest.main( verbosity = 2, exit = False )
    
    raw_input()
    