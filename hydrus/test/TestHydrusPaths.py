import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusPaths

class TestHydrusPaths( unittest.TestCase ):
    
    def test_eliding( self ):
        
        MAGIC_MAX_LENGTH = 220
        
        name_too_long = 'a' * 245
        name_shortened = 'a' * MAGIC_MAX_LENGTH
        
        self.assertEqual( HydrusPaths.ElideFilenameOrDirectorySafely( name_too_long ), name_shortened )
        
        unicode_name_too_long_hex = '57696e646f7773e381a7e381afe380814e544653e381aee5a0b4e59088e38081e9809ae5b8b8e38081e38395e382a1e382a4e383abe5908de381aee69c80e5a4a7e995b7e381af323630e69687e5ad97e381a7e38199e380826d61634f53efbc88556e6978e38399e383bce382b9efbc89e381a7e381afe380814846532be3818ae38288e381b341504653e381aee5a0b4e59088e38081e9809ae5b8b8e38081e38395e382a1e382a4e383abe5908de381aee69c80e5a4a7e995b7e381af323535e69687e5ad97e381a7e38199e380824c696e7578efbc88e3818ae38288e381b3e3819de381aee4bb96e381ae556e6978e7b3bbe382b7e382b9e38386e383a0efbc89e381a7e381afe38081e381bbe381a8e38293e381a9e381aee38395e382a1e382a4e383abe382b7e382b9e38386e383a0e38081e4be8be38188e381b065787434e381aee5a0b4e59088e38081e9809ae5b8b8e38081e38395e382a1e382a4e383abe5908de381aee69c80e5a4a7e995b7e381af323535e69687e5ad97e381a7e38199e38082'
        
        unicode_name_too_long = bytes.fromhex( unicode_name_too_long_hex ).decode( 'utf-8' )
        
        unicode_name_shortened_hex = '57696e646f7773e381a7e381afe380814e544653e381aee5a0b4e59088e38081e9809ae5b8b8e38081e38395e382a1e382a4e383abe5908de381aee69c80e5a4a7e995b7e381af323630e69687e5ad97e381a7e38199e380826d61634f53efbc88556e6978e38399e383bce382b9efbc89e381a7e381afe380814846532be3818ae38288e381b341504653e381aee5a0b4e59088e38081e9809ae5b8b8e38081e38395e382a1e382a4e383abe5908de381aee69c80e5a4a7e995b7e381af323535e69687e5ad97e381a7e38199e380824c696e7578efbc88e3818a'
        
        unicode_name_shortened = bytes.fromhex( unicode_name_shortened_hex ).decode( 'utf-8' )
        
        self.assertEqual( HydrusPaths.ElideFilenameOrDirectorySafely( unicode_name_too_long ), unicode_name_shortened )
        
        #
        
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        num_characters_used_in_other_components = 4
        
        try:
            
            HC.PLATFORM_WINDOWS = True
            
            name_shortened = 'a' * ( MAGIC_MAX_LENGTH - num_characters_used_in_other_components )
            
            self.assertEqual( HydrusPaths.ElideFilenameOrDirectorySafely( name_too_long, num_characters_used_in_other_components = num_characters_used_in_other_components ), name_shortened )
            
            HC.PLATFORM_WINDOWS = False
            
            name_shortened = 'a' * MAGIC_MAX_LENGTH
            
            self.assertEqual( HydrusPaths.ElideFilenameOrDirectorySafely( name_too_long, num_characters_used_in_other_components = num_characters_used_in_other_components ), name_shortened )
            
        finally:
            
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
        num_characters_already_used_in_this_component = 3
        
        name_shortened = 'a' * ( MAGIC_MAX_LENGTH - num_characters_already_used_in_this_component )
        
        self.assertEqual( HydrusPaths.ElideFilenameOrDirectorySafely( name_too_long, num_characters_already_used_in_this_component = num_characters_already_used_in_this_component ), name_shortened )
        
        #
        
        
        
    
