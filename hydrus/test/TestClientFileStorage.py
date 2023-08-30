import itertools
import os
import shutil
import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientFilesPhysical

def get_good_prefixes():
    
    good_prefixes = [ f'f{prefix}' for prefix in HydrusData.IterateHexPrefixes() ]
    good_prefixes.extend( [ f't{prefix}' for prefix in HydrusData.IterateHexPrefixes() ] )
    
    return good_prefixes
    

class TestClientFileStorage( unittest.TestCase ):
    
    def test_functions( self ):
        
        hex_chars = '0123456789abcdef'
        
        good_prefixes = get_good_prefixes()
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 'f', good_prefixes ), [] )
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 't', good_prefixes ), [] )
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 'f1', good_prefixes ), [] )
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 't6', good_prefixes ), [] )
        
        #
        
        # testing here that the implicit 'report two char length at least' thing works, so if we remove a whole contiguous segment, it reports the longer result and not 'f1'
        f1_series = [ 'f1' + c for c in hex_chars ]
        
        good_prefixes = get_good_prefixes()
        
        for prefix in f1_series:
            
            good_prefixes.remove( prefix )
            
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 'f', good_prefixes ), f1_series )
        
        #
        
        hex_chars = '0123456789abcdef'
        
        good_prefixes = get_good_prefixes()
        
        good_prefixes.append( 'f14' )
        good_prefixes.append( 't63' )
        
        good_prefixes.append( 'f145' )
        good_prefixes.append( 't634' )
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 'f', good_prefixes ), [] )
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 't', good_prefixes ), [] )
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 'f1', good_prefixes ), [] )
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 't6', good_prefixes ), [] )
        
        #
        
        # same deal but missing everything
        good_prefixes = [ prefix for prefix in get_good_prefixes() if prefix.startswith( 'f' ) ]
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 'f', [] ), good_prefixes )
        
        #
        
        good_prefixes = get_good_prefixes()
        
        good_prefixes.remove( 'f53' )
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 'f', good_prefixes ), [ 'f53' ] )
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 't', good_prefixes ), [] )
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 'f5', good_prefixes ), [ 'f53' ] )
        
        #
        
        good_prefixes = get_good_prefixes()
        
        good_prefixes.remove( 't11' )
        good_prefixes.extend( [ f't11{i}' for i in hex_chars ] )
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 't', good_prefixes ), [] )
        
        good_prefixes.remove( 't46' )
        good_prefixes.remove( 't115' )
        
        self.assertEqual( ClientFilesPhysical.GetMissingPrefixes( 't', good_prefixes ), [ 't115', 't46' ] )
        
        #
        
        good_prefixes = get_good_prefixes()
        
        good_prefixes = [ f'f{prefix}' for prefix in HydrusData.IterateHexPrefixes() ]
        good_prefixes.extend( [ f't{prefix}' for prefix in HydrusData.IterateHexPrefixes() ] )
        
        ClientFilesPhysical.CheckFullPrefixCoverage( 'f', good_prefixes )
        ClientFilesPhysical.CheckFullPrefixCoverage( 't', good_prefixes )
        
        good_prefixes.remove( 'f00' )
        good_prefixes.remove( 't06' )
        
        with self.assertRaises( HydrusExceptions.DataMissing ):
            
            ClientFilesPhysical.CheckFullPrefixCoverage( 'f', good_prefixes )
            
        
        with self.assertRaises( HydrusExceptions.DataMissing ):
            
            ClientFilesPhysical.CheckFullPrefixCoverage( 't', good_prefixes )
            
        
        
    
