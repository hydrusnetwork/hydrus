import os
import unittest

from hydrus.core import HydrusExceptions
from hydrus.core.files import HydrusFilesPhysicalStorage

from hydrus.client.files import ClientFilesPhysical

from hydrus.test import TestGlobals as TG

def get_good_prefixes():
    
    good_prefixes = list( HydrusFilesPhysicalStorage.IteratePrefixes( 'f' ) )
    good_prefixes.extend( HydrusFilesPhysicalStorage.IteratePrefixes( 't' ) )
    
    return good_prefixes
    

class TestClientFileStorage( unittest.TestCase ):
    
    def test_base_locations( self ):
        
        path = os.path.join( TG.test_controller.db_dir, 'client_files' )
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 1 )
        
        self.assertTrue( base_location.HasNoUpperLimit() )
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 1, max_num_bytes = 1024 )
        
        self.assertFalse( base_location.HasNoUpperLimit() )
        
        #
        
        subfolder_size = 1048567 * 122
        weight_of_subfolder = 1 / 256
        
        # 2/5, no weight limit, should be aiming for ~100 subfolders
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 2 )
        
        current_num_subfolders = 16
        
        self.assertEqual( base_location.NeedsToRemoveSubfolders( subfolder_size * current_num_subfolders ), False )
        self.assertEqual( base_location.WouldLikeToRemoveSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder ), False )
        self.assertEqual( base_location.EagerToAcceptSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder, subfolder_size * current_num_subfolders, subfolder_size ), True )
        self.assertEqual( base_location.AbleToAcceptSubfolders( subfolder_size * current_num_subfolders, subfolder_size ), True )
        
        current_num_subfolders = 128
        
        self.assertEqual( base_location.NeedsToRemoveSubfolders( subfolder_size * current_num_subfolders ), False )
        self.assertEqual( base_location.WouldLikeToRemoveSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder ), True )
        self.assertEqual( base_location.EagerToAcceptSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder, subfolder_size * current_num_subfolders, subfolder_size ), False )
        self.assertEqual( base_location.AbleToAcceptSubfolders( subfolder_size * current_num_subfolders, subfolder_size ), True )
        
        # max num files of ~20 subfolders
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 2, max_num_bytes = subfolder_size * 20 )
        
        current_num_subfolders = 16
        
        self.assertEqual( base_location.NeedsToRemoveSubfolders( subfolder_size * current_num_subfolders ), False )
        self.assertEqual( base_location.WouldLikeToRemoveSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder ), False )
        self.assertEqual( base_location.EagerToAcceptSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder, subfolder_size * current_num_subfolders, subfolder_size ), True )
        self.assertEqual( base_location.AbleToAcceptSubfolders( subfolder_size * current_num_subfolders, subfolder_size ), True )
        
        current_num_subfolders = 32
        
        self.assertEqual( base_location.NeedsToRemoveSubfolders( subfolder_size * current_num_subfolders ), True )
        self.assertEqual( base_location.WouldLikeToRemoveSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder ), False )
        self.assertEqual( base_location.EagerToAcceptSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder, subfolder_size * current_num_subfolders, subfolder_size ), False )
        self.assertEqual( base_location.AbleToAcceptSubfolders( subfolder_size * current_num_subfolders, subfolder_size ), False )
        
        # max num files of ~500 subfolders
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 2, max_num_bytes = subfolder_size * 500 )
        
        current_num_subfolders = 16
        
        self.assertEqual( base_location.NeedsToRemoveSubfolders( subfolder_size * current_num_subfolders ), False )
        self.assertEqual( base_location.WouldLikeToRemoveSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder ), False )
        self.assertEqual( base_location.EagerToAcceptSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder, subfolder_size * current_num_subfolders, subfolder_size ), True )
        self.assertEqual( base_location.AbleToAcceptSubfolders( subfolder_size * current_num_subfolders, subfolder_size ), True )
        
        current_num_subfolders = 128
        
        self.assertEqual( base_location.NeedsToRemoveSubfolders( subfolder_size * current_num_subfolders ), False )
        self.assertEqual( base_location.WouldLikeToRemoveSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder ), True )
        self.assertEqual( base_location.EagerToAcceptSubfolders( weight_of_subfolder * current_num_subfolders, 5, weight_of_subfolder, subfolder_size * current_num_subfolders, subfolder_size ), False )
        self.assertEqual( base_location.AbleToAcceptSubfolders( subfolder_size * current_num_subfolders, subfolder_size ), True )
        
        # edge-case adding
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( path, 2, max_num_bytes = 100 )
        
        self.assertEqual( base_location.EagerToAcceptSubfolders( 0.35, 5, 0.03, 90, 5 ), True )
        self.assertEqual( base_location.EagerToAcceptSubfolders( 0.35, 5, 0.07, 90, 5 ), False )
        self.assertEqual( base_location.EagerToAcceptSubfolders( 0.35, 5, 0.03, 90, 11 ), False )
        
        self.assertEqual( base_location.AbleToAcceptSubfolders( 90, 5 ), True )
        self.assertEqual( base_location.AbleToAcceptSubfolders( 90, 11 ), False )
        
        
    
    def test_subfolders( self ):
        
        muh_test_base_location = ClientFilesPhysical.FilesStorageBaseLocation( os.path.join( TG.test_controller.db_dir, 'client_files' ), 1 )
        
        subfolder = ClientFilesPhysical.FilesStorageSubfolder( 'ta', muh_test_base_location )
        
        self.assertEqual( subfolder.path, os.path.join( muh_test_base_location.path, 'ta' ) )
        
        subfolder = ClientFilesPhysical.FilesStorageSubfolder( 'fab', muh_test_base_location )
        
        self.assertEqual( subfolder.path, os.path.join( muh_test_base_location.path, 'fab' ) )
        
        subfolder = ClientFilesPhysical.FilesStorageSubfolder( 'fab3', muh_test_base_location )
        
        self.assertEqual( subfolder.path, os.path.join( muh_test_base_location.path, 'fab', '3' ) )
        
    
    def test_functions( self ):
        
        hex_chars = '0123456789abcdef'
        
        good_prefixes = get_good_prefixes()
        
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', good_prefixes ), [] )
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 't', good_prefixes ), [] )
        
        #
        
        # testing here that the implicit 'report two char length at least' thing works, so if we remove a whole contiguous segment, it reports the longer result and not 'f1'
        f1_series = [ 'f1' + c for c in hex_chars ]
        
        good_prefixes = get_good_prefixes()
        
        for prefix in f1_series:
            
            good_prefixes.remove( prefix )
            
        
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', good_prefixes ), f1_series )
        
        #
        
        # same deal but missing everything
        good_prefixes = [ prefix for prefix in get_good_prefixes() if prefix.startswith( 'f' ) ]
        
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', [] ), good_prefixes )
        
        #
        
        good_prefixes = get_good_prefixes()
        
        good_prefixes.remove( 'f53' )
        
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', good_prefixes ), [ 'f53' ] )
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 't', good_prefixes ), [] )
        
        #
        
        good_prefixes = get_good_prefixes()
        
        HydrusFilesPhysicalStorage.CheckFullPrefixCoverage( 'f', good_prefixes )
        HydrusFilesPhysicalStorage.CheckFullPrefixCoverage( 't', good_prefixes )
        
        good_prefixes.remove( 'f00' )
        good_prefixes.remove( 't06' )
        
        with self.assertRaises( HydrusExceptions.DataMissing ):
            
            HydrusFilesPhysicalStorage.CheckFullPrefixCoverage( 'f', good_prefixes )
            
        
        with self.assertRaises( HydrusExceptions.DataMissing ):
            
            HydrusFilesPhysicalStorage.CheckFullPrefixCoverage( 't', good_prefixes )
            
        
        
    
