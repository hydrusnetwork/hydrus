from unittest import mock
import unittest

import ntpath
import posixpath

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
            
            with mock.patch( 'os.path', ntpath ):
                
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
            
            with mock.patch( 'os.path', posixpath ):
                
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
            
            with mock.patch( 'os.path', ntpath ):
                
                directory_prefix = 'C:\\hydrus\\files'
                ext = '.png'
                
                name_too_long = 'a' * 245
                name_shortened = 'a' * ( max_num_characters - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
                
                name_too_long = a_hiragana * 245
                name_shortened = a_hiragana * ( max_num_characters - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( name_too_long, max_num_characters, directory_prefix, ext ), name_shortened )
                
            
            #
            
            with mock.patch( 'os.path', posixpath ):
                
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
            
            with mock.patch( 'os.path', ntpath ):
                
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
            
            with mock.patch( 'os.path', posixpath ):
                
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
            
            with mock.patch( 'os.path', ntpath ):
                
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
            
            with mock.patch( 'os.path', posixpath ):
                
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
            
        
    
    def test_4_eliding_subdirs_with_whitespace( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                result = HydrusPaths.SanitizePathForExport( 'd \\file ', True )
                expected_result = 'd\\file'
                
                self.assertEqual( result, expected_result )
                
                result = HydrusPaths.SanitizePathForExport( 'd' + ' ' * 512 + 'd\\file ', True )
                expected_result = 'd\\file'
                
                self.assertEqual( result, expected_result )
                
                result = HydrusPaths.ElideFilenameSafely( 'file ', 64, 'C:\\hydrus\\files\\d', '.jpg' )
                expected_result = 'file'
                
                self.assertEqual( result, expected_result )
                
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            #
            
            with mock.patch( 'os.path', posixpath ):
                
                result = HydrusPaths.SanitizePathForExport( 'd /file ', False )
                expected_result = 'd/file'
                
                self.assertEqual( result, expected_result )
                
                result = HydrusPaths.SanitizePathForExport( 'd' + ' ' * 2048 + 'd/file ', False )
                expected_result = 'd/file'
                
                self.assertEqual( result, expected_result )
                
                result = HydrusPaths.ElideFilenameSafely( 'file ', 64, '/mnt/hydrus/files/d', '.jpg' )
                expected_result = 'file'
                
                self.assertEqual( result, expected_result )
                
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
    def test_5_removing_ntfs_gubbins( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                result = HydrusPaths.SanitizePathForExport( 'con\\com1', True )
                expected_result = 'con_\\com1_'
                
                self.assertEqual( result, expected_result )
                
                result = HydrusPaths.SanitizePathForExport( 'test. . \\hello . .', True )
                expected_result = 'test\\hello'
                
                self.assertEqual( result, expected_result )
                
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
