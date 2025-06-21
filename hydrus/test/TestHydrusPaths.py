import unittest

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusPaths

# I pad these in the actual code
MAGIC_WINDOWS_TOTAL_PATH_LIMIT = 260 - 10
MAGIC_LINUX_TOTAL_PATH_LIMIT = 4096 - 20

class TestHydrusPaths( unittest.TestCase ):
    
    def test_0_eliding_none( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            max_num_characters = 220
            
            a_hiragana = '\u3042'
            
            #
            
            directory_prefix = 'C:\\hydrus\\files'
            ext = '.png'
            
            name_normal = 'a' * 20
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_normal, max_num_characters, directory_prefix, ext ), name_normal )
            
            name_normal = a_hiragana * 20
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_normal, max_num_characters, directory_prefix, ext ), name_normal )
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            directory_prefix = '/mnt/hydrus'
            ext = '.png'
            
            name_normal = 'a' * 20
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_normal, max_num_characters, directory_prefix, ext ), name_normal )
            
            name_normal = a_hiragana * 20
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_normal, max_num_characters, directory_prefix, ext ), name_normal )
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
    def test_1_eliding_simple( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            max_num_characters = 220
            
            a_hiragana = '\u3042'
            
            #
            
            directory_prefix = 'C:\\hydrus\\files'
            ext = '.png'
            
            name_too_long = 'a' * 245
            name_shortened = 'a' * ( max_num_characters - len( ext ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
            
            name_too_long = a_hiragana * 245
            name_shortened = a_hiragana * ( max_num_characters - len( ext ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            directory_prefix = '/mnt/hydrus'
            ext = '.png'
            
            name_too_long = 'a' * 245
            name_shortened = 'a' * ( max_num_characters - len( ext ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
            
            name_too_long = a_hiragana * 245
            
            name_shortened = ''
            
            len_one_char = len( a_hiragana.encode( 'utf-8' ) )
            
            while len( name_shortened.encode( 'utf-8' ) ) + len_one_char <= ( max_num_characters - len( ext.encode( 'utf-8' ) ) ):
                
                name_shortened += a_hiragana
                
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
    def test_2_eliding_with_path( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            max_num_characters = 220
            
            a_hiragana = '\u3042'
            
            #
            
            directory_prefix = 'C:\\hydrus\\files\\' + ( 'd' * ( MAGIC_WINDOWS_TOTAL_PATH_LIMIT - int( 245 / 2 ) ) )
            ext = '.png'
            
            name_too_long = 'a' * 245
            name_shortened = 'a' * ( MAGIC_WINDOWS_TOTAL_PATH_LIMIT - len( directory_prefix ) - 1 - len( ext ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
            
            name_too_long = a_hiragana * 245
            name_shortened = a_hiragana * ( MAGIC_WINDOWS_TOTAL_PATH_LIMIT - len( directory_prefix ) - 1 - len( ext ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            #
            
            directory_prefix = '/mnt/hydrus/files/' + ( 'd' * ( MAGIC_LINUX_TOTAL_PATH_LIMIT - int( 245 / 2 ) ) ) 
            ext = '.png'
            
            name_too_long = 'a' * 245
            name_shortened = 'a' * ( MAGIC_LINUX_TOTAL_PATH_LIMIT - len( directory_prefix ) - 1 - len( ext ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
            
            name_too_long = a_hiragana * 245
            name_shortened = ''
            
            len_one_char = len( a_hiragana.encode( 'utf-8' ) )
            
            while len( name_shortened.encode( 'utf-8' ) ) + len_one_char <= ( MAGIC_LINUX_TOTAL_PATH_LIMIT - len( directory_prefix ) - 1 - len( ext ) ):
                
                name_shortened += a_hiragana
                
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
    def test_3_eliding_to_short_result( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            short_max_num_characters = 12
            
            a_hiragana = '\u3042'
            
            #
            
            directory_prefix = 'C:\\hydrus\\files\\' + ( 'd' * ( MAGIC_WINDOWS_TOTAL_PATH_LIMIT - int( 245 / 2 ) ) )
            ext = '.png'
            
            name_too_long = 'a' * 245
            name_shortened = 'a' * ( short_max_num_characters - len( ext ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, short_max_num_characters, directory_prefix, ext ), name_shortened )
            
            name_too_long = a_hiragana * 245
            name_shortened = a_hiragana * ( short_max_num_characters - len( ext ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, short_max_num_characters, directory_prefix, ext ), name_shortened )
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            #
            
            directory_prefix = '/mnt/hydrus/files/' + ( 'd' * ( MAGIC_LINUX_TOTAL_PATH_LIMIT - int( 245 / 2 ) ) ) 
            ext = '.png'
            
            name_too_long = 'a' * 245
            name_shortened = 'a' * ( short_max_num_characters - len( ext.encode( 'utf-8' ) ) )
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, short_max_num_characters, directory_prefix, ext ), name_shortened )
            
            name_too_long = a_hiragana * 245
            name_shortened = ''
            
            len_one_char = len( a_hiragana.encode( 'utf-8' ) )
            
            while len( name_shortened.encode( 'utf-8' ) ) + len_one_char <= ( short_max_num_characters - len( ext.encode( 'utf-8' ) ) ):
                
                name_shortened += a_hiragana
                
            
            self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, short_max_num_characters, directory_prefix, ext ), name_shortened )
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
