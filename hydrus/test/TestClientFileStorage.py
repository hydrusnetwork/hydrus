import os
import unittest

from hydrus.core import HydrusExceptions
from hydrus.core import HydrusPaths
from hydrus.core import HydrusTemp
from hydrus.core.files import HydrusFilesPhysicalStorage

from hydrus.client import ClientThreading
from hydrus.client.files import ClientFilesPhysical

from hydrus.test import TestGlobals as TG

def get_good_prefixes():
    
    good_prefixes = list( HydrusFilesPhysicalStorage.IteratePrefixes( 'f', HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ) )
    good_prefixes.extend( HydrusFilesPhysicalStorage.IteratePrefixes( 't', HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ) )
    
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
        
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ), [] )
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 't', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ), [] )
        
        #
        
        # testing here that the implicit 'report two char length at least' thing works, so if we remove a whole contiguous segment, it reports the longer result and not 'f1'
        f1_series = [ 'f1' + c for c in hex_chars ]
        
        good_prefixes = get_good_prefixes()
        
        for prefix in f1_series:
            
            good_prefixes.remove( prefix )
            
        
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ), f1_series )
        
        #
        
        # same deal but missing everything
        good_prefixes = [ prefix for prefix in get_good_prefixes() if prefix.startswith( 'f' ) ]
        
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', [], HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ), good_prefixes )
        
        #
        
        good_prefixes = get_good_prefixes()
        
        good_prefixes.remove( 'f53' )
        
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 'f', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ), [ 'f53' ] )
        self.assertEqual( HydrusFilesPhysicalStorage.GetMissingPrefixes( 't', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH ), [] )
        
        #
        
        good_prefixes = get_good_prefixes()
        
        HydrusFilesPhysicalStorage.CheckFullPrefixCoverage( 'f', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH )
        HydrusFilesPhysicalStorage.CheckFullPrefixCoverage( 't', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH )
        
        good_prefixes.remove( 'f00' )
        good_prefixes.remove( 't06' )
        
        with self.assertRaises( HydrusExceptions.DataMissing ):
            
            HydrusFilesPhysicalStorage.CheckFullPrefixCoverage( 'f', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH )
            
        
        with self.assertRaises( HydrusExceptions.DataMissing ):
            
            HydrusFilesPhysicalStorage.CheckFullPrefixCoverage( 't', good_prefixes, HydrusFilesPhysicalStorage.DEFAULT_PREFIX_LENGTH )
            
        
        
    

class TestClientGranularisation( unittest.TestCase ):
    
    def test_2to3( self ):
        
        test_dir = HydrusTemp.GetSubTempDir( 'test_granularisation_2to3' )
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( test_dir, 1 )
        
        for prefix_type in [ 'f', 't' ]:
            
            for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, 2 ):
                
                subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
                
                HydrusPaths.MakeSureDirectoryExists( subfolder.path )
                
            
        
        job_status = ClientThreading.JobStatus()
        
        ClientFilesPhysical.RegranulariseBaseLocation( [ base_location.path ], [ 'f', 't' ], 2, 3, job_status )
        
        num_done = 0
        
        for prefix_type in [ 'f', 't' ]:
            
            for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, 3 ):
                
                subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
                
                self.assertTrue( subfolder.PathExists() )
                
                num_done += 1
                
            
        
        self.assertEqual( num_done, 2 * ( 16 ** 3 ) )
        
        HydrusPaths.DeletePath( test_dir )
        
    
    def test_3to2( self ):
        
        test_dir = HydrusTemp.GetSubTempDir( 'test_granularisation_3to2' )
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( test_dir, 1 )
        
        for prefix_type in [ 'f', 't' ]:
            
            for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, 3 ):
                
                subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
                
                HydrusPaths.MakeSureDirectoryExists( subfolder.path )
                
            
        
        job_status = ClientThreading.JobStatus()
        
        ClientFilesPhysical.RegranulariseBaseLocation( [ base_location.path ], [ 'f', 't' ], 3, 2, job_status )
        
        num_done = 0
        
        for prefix_type in [ 'f', 't' ]:
            
            for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, 3 ):
                
                subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
                
                self.assertFalse( subfolder.PathExists() )
                
            
            for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, 2 ):
                
                subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
                
                self.assertTrue( subfolder.PathExists() )
                
                num_done += 1
                
            
        
        self.assertEqual( num_done, 2 * ( 16 ** 2 ) )
        
        HydrusPaths.DeletePath( test_dir )
        
    
    def test_cancel( self ):
        
        test_dir = HydrusTemp.GetSubTempDir( 'test_granularisation_cancel' )
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( test_dir, 1 )
        
        for prefix_type in [ 'f' ]:
            
            for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, 2 ):
                
                subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
                
                HydrusPaths.MakeSureDirectoryExists( subfolder.path )
                
                if prefix == 'f83':
                    
                    with open( subfolder.GetFilePath( os.urandom(32).hex() ), 'wb' ) as f:
                        
                        f.write( b'hello' )
                        
                    
                
            
        
        job_status = ClientThreading.JobStatus()
        
        job_status.Cancel()
        
        with self.assertRaises( HydrusExceptions.CancelledException ):
            
            ClientFilesPhysical.RegranulariseBaseLocation( [ base_location.path ], [ 'f' ], 2, 3, job_status )
            
        
        HydrusPaths.DeletePath( test_dir )
        
    
    def test_2_detection( self ):
        
        test_dir = HydrusTemp.GetSubTempDir( 'test_granularisation_2_detection' )
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( test_dir, 1 )
        
        for prefix_type in [ 'f', 't' ]:
            
            for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, 2 ):
                
                subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
                
                HydrusPaths.MakeSureDirectoryExists( subfolder.path )
                
            
        
        self.assertEqual( ClientFilesPhysical.EstimateBaseLocationGranularity( test_dir ), 2 )
        
        HydrusPaths.DeletePath( test_dir )
        
    
    def test_3_detection( self ):
        
        test_dir = HydrusTemp.GetSubTempDir( 'test_granularisation_3_detection' )
        
        base_location = ClientFilesPhysical.FilesStorageBaseLocation( test_dir, 1 )
        
        for prefix_type in [ 'f' ]:
            
            for prefix in HydrusFilesPhysicalStorage.IteratePrefixes( prefix_type, 3 ):
                
                subfolder = ClientFilesPhysical.FilesStorageSubfolder( prefix, base_location )
                
                HydrusPaths.MakeSureDirectoryExists( subfolder.path )
                
            
        
        self.assertEqual( ClientFilesPhysical.EstimateBaseLocationGranularity( test_dir ), 3 )
        
        HydrusPaths.DeletePath( test_dir )
        
    
    def test_mysterious_detection( self ):
        
        test_dir = HydrusTemp.GetSubTempDir( 'test_granularisation_empty_detection' )
        
        self.assertIs( ClientFilesPhysical.EstimateBaseLocationGranularity( test_dir ), None )
        
        HydrusPaths.DeletePath( test_dir )
        
        #
        
        test_dir = HydrusTemp.GetSubTempDir( 'test_granularisation_none_detection' )
        
        HydrusPaths.MakeSureDirectoryExists( os.path.join( test_dir, 'u wot mate' ) )
        
        self.assertIs( ClientFilesPhysical.EstimateBaseLocationGranularity( test_dir ), None )
        
        HydrusPaths.DeletePath( test_dir )
        
    
