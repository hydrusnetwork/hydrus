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
            
            a_hiragana = '\u3042'
            
            path_character_limit = None
            dirname_character_limit = None
            filename_character_limit = 220
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                force_ntfs_rules = True
                
                directory_prefix = 'C:\\hydrus\\files'
                ext = '.png'
                
                name_normal = 'a' * 20
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_normal, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_normal ) )
                
                name_normal = a_hiragana * 20
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_normal, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_normal ) )
                
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            with mock.patch( 'os.path', posixpath ):
                
                force_ntfs_rules = False
                
                directory_prefix = '/mnt/hydrus'
                ext = '.png'
                
                name_normal = 'a' * 20
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_normal, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_normal ) )
                
                name_normal = a_hiragana * 20
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_normal, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_normal ) )
                
            
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
            
            a_hiragana = '\u3042'
            
            path_character_limit = None
            dirname_character_limit = None
            filename_character_limit = 220
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                force_ntfs_rules = True
                
                directory_prefix = 'C:\\hydrus\\files'
                ext = '.png'
                
                name_too_long = 'a' * 245
                name_shortened = 'a' * ( filename_character_limit - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
                name_too_long = a_hiragana * 245
                name_shortened = a_hiragana * ( filename_character_limit - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
            
            #
            
            with mock.patch( 'os.path', posixpath ):
                
                # bytes, not chars
                HC.PLATFORM_WINDOWS = False
                HC.PLATFORM_LINUX = True
                
                force_ntfs_rules = False
                
                directory_prefix = '/mnt/hydrus'
                ext = '.png'
                
                name_too_long = 'a' * 245
                name_shortened = 'a' * ( filename_character_limit - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
                name_too_long = a_hiragana * 245
                
                name_shortened = ''
                
                len_one_char = len( a_hiragana.encode( 'utf-8' ) )
                
                while len( name_shortened.encode( 'utf-8' ) ) + len_one_char <= ( filename_character_limit - len( ext.encode( 'utf-8' ) ) ):
                    
                    name_shortened += a_hiragana
                    
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
            
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
            
            path_character_limit = None
            dirname_character_limit = None
            filename_character_limit = 220
            
            a_hiragana = '\u3042'
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                force_ntfs_rules = True
                
                directory_prefix = 'C:\\hydrus\\files\\' + ( 'd' * ( MAGIC_WINDOWS_TOTAL_PATH_LIMIT - int( 245 / 2 ) ) )
                ext = '.png'
                
                name_too_long = 'a' * 245
                name_shortened = 'a' * ( MAGIC_WINDOWS_TOTAL_PATH_LIMIT - len( directory_prefix ) - 1 - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
                name_too_long = a_hiragana * 245
                name_shortened = a_hiragana * ( MAGIC_WINDOWS_TOTAL_PATH_LIMIT - len( directory_prefix ) - 1 - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            #
            
            with mock.patch( 'os.path', posixpath ):
                
                force_ntfs_rules = False
                
                directory_prefix = '/mnt/hydrus/files/' + ( 'd' * ( MAGIC_LINUX_TOTAL_PATH_LIMIT - int( 245 / 2 ) ) ) 
                ext = '.png'
                
                name_too_long = 'a' * 245
                name_shortened = 'a' * ( MAGIC_LINUX_TOTAL_PATH_LIMIT - len( directory_prefix ) - 1 - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
                name_too_long = a_hiragana * 245
                name_shortened = ''
                
                len_one_char = len( a_hiragana.encode( 'utf-8' ) )
                
                while len( name_shortened.encode( 'utf-8' ) ) + len_one_char <= ( MAGIC_LINUX_TOTAL_PATH_LIMIT - len( directory_prefix ) - 1 - len( ext ) ):
                    
                    name_shortened += a_hiragana
                    
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
            
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
            
            a_hiragana = '\u3042'
            
            path_character_limit = None
            dirname_character_limit = None
            filename_character_limit = 12
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                force_ntfs_rules = True
                
                directory_prefix = 'C:\\hydrus\\files\\' + ( 'd' * ( MAGIC_WINDOWS_TOTAL_PATH_LIMIT - int( 245 / 2 ) ) )
                ext = '.png'
                
                name_too_long = 'a' * 245
                name_shortened = 'a' * ( filename_character_limit - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
                name_too_long = a_hiragana * 245
                name_shortened = a_hiragana * ( filename_character_limit - len( ext ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            #
            
            with mock.patch( 'os.path', posixpath ):
                
                force_ntfs_rules = False
                
                directory_prefix = '/mnt/hydrus/files/' + ( 'd' * ( MAGIC_LINUX_TOTAL_PATH_LIMIT - int( 245 / 2 ) ) ) 
                ext = '.png'
                
                name_too_long = 'a' * 245
                name_shortened = 'a' * ( filename_character_limit - len( ext.encode( 'utf-8' ) ) )
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
                name_too_long = a_hiragana * 245
                name_shortened = ''
                
                len_one_char = len( a_hiragana.encode( 'utf-8' ) )
                
                while len( name_shortened.encode( 'utf-8' ) ) + len_one_char <= ( filename_character_limit - len( ext.encode( 'utf-8' ) ) ):
                    
                    name_shortened += a_hiragana
                    
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, '', name_too_long, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( '', name_shortened ) )
                
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
    def test_4_eliding_subdirs( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            a_hiragana = '\u3042'
            
            path_character_limit = None
            dirname_character_limit = 8
            filename_character_limit = 220
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                force_ntfs_rules = True
                
                directory_prefix = 'C:\\hydrus\\files'
                ext = '.png'
                
                normal_name = 'a' * 10
                subdirs_elidable = 'a' * 20 + '\\' + 'a' * 20
                subdirs_elided = 'a' * 8 + '\\' + 'a' * 8
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, subdirs_elidable, normal_name, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( subdirs_elided, normal_name ) )
                
                normal_name = a_hiragana * 10
                subdirs_elidable = a_hiragana * 20 + '\\' + a_hiragana * 20
                subdirs_elided = a_hiragana * 8 + '\\' + a_hiragana * 8
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, subdirs_elidable, normal_name, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( subdirs_elided, normal_name ) )
                
            
            #
            
            with mock.patch( 'os.path', posixpath ):
                
                # bytes, not chars
                HC.PLATFORM_WINDOWS = False
                HC.PLATFORM_LINUX = True
                
                force_ntfs_rules = False
                
                directory_prefix = '/mnt/hydrus'
                ext = '.png'
                
                normal_name = 'a' * 10
                subdirs_elidable = 'a' * 20 + '/' + 'a' * 20
                subdirs_elided = 'a' * 8 + '/' + 'a' * 8
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, subdirs_elidable, normal_name, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( subdirs_elided, normal_name ) )
                
                normal_name = a_hiragana * 10
                subdirs_elidable = a_hiragana * 20 + '/' + a_hiragana * 20
                subdirs_elided = a_hiragana * 2 + '/' + a_hiragana * 2
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, subdirs_elidable, normal_name, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( subdirs_elided, normal_name ) )
                
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
    def test_5_eliding_path_length( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            a_hiragana = '\u3042'
            
            path_character_limit = 96
            dirname_character_limit = 8
            filename_character_limit = 220
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                force_ntfs_rules = True
                
                directory_prefix = 'C:\\hydrus\\files'
                ext = '.png'
                
                normal_name = 'a' * 40
                subdirs_elidable = 'a' * 20 + '\\' + 'a' * 20
                subdirs_elided = 'a' * 8 + '\\' + 'a' * 8
                name_shortened = normal_name[ : path_character_limit - len( subdirs_elided ) - 2 - len( directory_prefix ) - len( ext ) - 10 ]
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, subdirs_elidable, normal_name, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( subdirs_elided, name_shortened ) )
                
                normal_name = a_hiragana * 10
                subdirs_elidable = a_hiragana * 20 + '\\' + a_hiragana * 20
                subdirs_elided = a_hiragana * 8 + '\\' + a_hiragana * 8
                name_shortened = normal_name[ : path_character_limit - len( subdirs_elided ) - 2 - len( directory_prefix ) - len( ext ) - 10 ]
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, subdirs_elidable, normal_name, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( subdirs_elided, name_shortened ) )
                
            
            #
            
            with mock.patch( 'os.path', posixpath ):
                
                # bytes, not chars
                HC.PLATFORM_WINDOWS = False
                HC.PLATFORM_LINUX = True
                
                force_ntfs_rules = False
                
                directory_prefix = '/mnt/hydrus'
                ext = '.png'
                
                normal_name = 'a' * 10
                subdirs_elidable = 'a' * 20 + '/' + 'a' * 20
                subdirs_elided = 'a' * 8 + '/' + 'a' * 8
                name_shortened = normal_name[ : path_character_limit - len( subdirs_elided ) - 2 - len( directory_prefix ) - len( ext ) - 10 ]
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, subdirs_elidable, normal_name, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( subdirs_elided, name_shortened ) )
                
                normal_name = a_hiragana * 10
                subdirs_elidable = a_hiragana * 20 + '/' + a_hiragana * 20
                subdirs_elided = a_hiragana * 2 + '/' + a_hiragana * 2
                name_shortened = a_hiragana * 10 # this number was handed to me by a fairy
                
                self.assertEqual( HydrusPaths.ElideFilenameSafely( directory_prefix, subdirs_elidable, normal_name, ext, path_character_limit, dirname_character_limit, filename_character_limit, force_ntfs_rules ), ( subdirs_elided, name_shortened ) )
                
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
    def test_6_eliding_subdirs_with_whitespace( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            path_character_limit = None
            dirname_character_limit = None
            filename_character_limit = 220
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                force_ntfs_rules = True
                
                directory_prefix = 'C:\\hydrus\\files\\'
                ext = '.png'
                
                self.assertEqual(
                    HydrusPaths.ElideFilenameSafely(
                        directory_prefix,
                        'd ',
                        ' file ',
                        ext,
                        path_character_limit,
                        dirname_character_limit,
                        filename_character_limit,
                        force_ntfs_rules
                    ), 
                    ( 'd', 'file' )
                )
                
                self.assertEqual(
                    HydrusPaths.ElideFilenameSafely(
                        directory_prefix,
                        'd' + ' ' * 512 + 'd',
                        'file ',
                        ext,
                        path_character_limit,
                        dirname_character_limit,
                        filename_character_limit,
                        force_ntfs_rules
                    ), 
                    ( 'd', 'file' )
                )
                
            
            #
            
            # bytes, not chars
            HC.PLATFORM_WINDOWS = False
            HC.PLATFORM_LINUX = True
            
            #
            
            with mock.patch( 'os.path', posixpath ):
                
                force_ntfs_rules = False
                
                directory_prefix = '/mnt/hydrus'
                ext = '.png'
                
                self.assertEqual(
                    HydrusPaths.ElideFilenameSafely(
                        directory_prefix,
                        'd ',
                        ' file ',
                        ext,
                        path_character_limit,
                        dirname_character_limit,
                        filename_character_limit,
                        force_ntfs_rules
                    ), 
                    ( 'd', 'file' )
                )
                
                self.assertEqual(
                    HydrusPaths.ElideFilenameSafely(
                        directory_prefix,
                        'd' + ' ' * 2048 + 'd',
                        'file ',
                        ext,
                        path_character_limit,
                        dirname_character_limit,
                        filename_character_limit,
                        force_ntfs_rules
                    ), 
                    ( 'd', 'file' )
                )
                
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
    def test_7_removing_ntfs_gubbins( self ):
        
        old_platform_linux = HC.PLATFORM_LINUX
        old_platform_windows = HC.PLATFORM_WINDOWS
        
        try:
            
            path_character_limit = None
            dirname_character_limit = None
            filename_character_limit = 220
            
            # chars, not bytes
            HC.PLATFORM_WINDOWS = True
            HC.PLATFORM_LINUX = False
            
            #
            
            with mock.patch( 'os.path', ntpath ):
                
                force_ntfs_rules = True
                
                directory_prefix = 'C:\\hydrus\\files\\'
                ext = '.png'
                
                self.assertEqual(
                    HydrusPaths.ElideFilenameSafely(
                        directory_prefix,
                        'con\\aux',
                        'com1',
                        ext,
                        path_character_limit,
                        dirname_character_limit,
                        filename_character_limit,
                        force_ntfs_rules
                    ), 
                    ( 'co\\au', 'com' )
                )
                
                self.assertEqual(
                    HydrusPaths.ElideFilenameSafely(
                        directory_prefix,
                        'test. . \\test2. . ',
                        'hello . .',
                        ext,
                        path_character_limit,
                        dirname_character_limit,
                        filename_character_limit,
                        force_ntfs_rules
                    ),
                    ( 'test\\test2', 'hello' )
                )
                
            
        finally:
            
            HC.PLATFORM_LINUX = old_platform_linux
            HC.PLATFORM_WINDOWS = old_platform_windows
            
        
    
