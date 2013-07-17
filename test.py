from include import HydrusConstants as HC
from include import TestConstants
from include import TestDB
from include import TestFunctions
from include import TestHydrusTags
import unittest

if __name__ == '__main__':
    
    app = TestConstants.App()
    
    suites = []
    
    suites.append( unittest.TestLoader().loadTestsFromModule( TestDB ) )
    suites.append( unittest.TestLoader().loadTestsFromModule( TestFunctions ) )
    suites.append( unittest.TestLoader().loadTestsFromModule( TestHydrusTags ) )
    
    suite = unittest.TestSuite( suites )
    
    unittest.TextTestRunner( verbosity = 1 ).run( suite )
    
    raw_input()
    