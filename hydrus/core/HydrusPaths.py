import collections.abc
import functools
import os
import re
import send2trash
import shlex
import shutil
import stat
import threading
import time
import traceback
import typing

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPSUtil
from hydrus.core import HydrusTime
from hydrus.core.processes import HydrusSubprocess
from hydrus.core.processes import HydrusThreading

def stat_is_file( path_stat: os.stat_result ):
    
    return stat.S_ISREG( path_stat.st_mode )
    

def stat_is_symlink( path_stat: os.stat_result ):
    
    return stat.S_ISLNK( path_stat.st_mode )
    

def stat_is_dir( path_stat: os.stat_result ):
    
    return stat.S_ISDIR( path_stat.st_mode )
    

def stat_is_samefile( source_stat: os.stat_result, dest_stat: os.stat_result ):
    """
    This guy replicates os.path.samefile but with the stat calls ready aforehand.
    """
    
    return source_stat.st_dev == dest_stat.st_dev and source_stat.st_ino == dest_stat.st_ino
    

def AppendPathUntilNoConflicts( path ):
    
    ( path_absent_ext, ext ) = os.path.splitext( path )
    
    good_path_absent_ext = path_absent_ext
    
    i = 0
    
    while os.path.exists( good_path_absent_ext + ext ):
        
        good_path_absent_ext = path_absent_ext + '_' + str( i )
        
        i += 1
        
    
    return good_path_absent_ext + ext
    
def ConvertAbsPathToPortablePath( abs_path, base_dir_override = None ):
    
    try:
        
        if base_dir_override is None:
            
            base_dir = HG.controller.GetDBDir()
            
        else:
            
            base_dir = base_dir_override
            
        
        portable_path = os.path.relpath( abs_path, base_dir )
        
        if portable_path.startswith( '..' ):
            
            portable_path = abs_path
            
        
    except:
        
        portable_path = abs_path
        
    
    if HC.PLATFORM_WINDOWS:
        
        portable_path = portable_path.replace( '\\', '/' ) # store seps as /, to maintain multiplatform uniformity
        
    
    return portable_path
    

def ConvertPortablePathToAbsPath( portable_path, base_dir_override = None ):
    
    portable_path = os.path.normpath( portable_path ) # collapses .. stuff and converts / to \\ for windows only
    
    if os.path.isabs( portable_path ):
        
        abs_path = portable_path
        
    else:
        
        if base_dir_override is None:
            
            base_dir = HG.controller.GetDBDir()
            
        else:
            
            base_dir = base_dir_override
            
        
        abs_path = os.path.normpath( os.path.join( base_dir, portable_path ) )
        
    
    # is this sensible, what am I trying to do here? recover from a legacy platform migration maybe, from perhaps when I stored backslashes in portable paths?
    if not HC.PLATFORM_WINDOWS and not os.path.exists( abs_path ):
        
        abs_path = abs_path.replace( '\\', '/' )
        
    
    return abs_path
    

def CopyFileLikeToFileLike( f_source, f_dest ):
    
    for block in ReadFileLikeAsBlocks( f_source ): f_dest.write( block )
    

def DeletePath( path ) -> bool:
    
    if HG.file_report_mode:
        
        HydrusData.ShowText( 'Deleting {}'.format( path ) )
        
        HydrusData.ShowText( ''.join( traceback.format_stack() ) )
        
    
    try:
        
        path_stat_nofollow = os.stat( path, follow_symlinks = False ) # this is the stat on the path as-is. if it is a symlink, we looking at it, not where it points
        
    except FileNotFoundError:
        
        return True
        
    
    if stat_is_symlink( path_stat_nofollow ):
        
        # ok we have been given a dir or file that actually exists elsewhere. we don't want to delete that guy, we want to delete this link
        
        try:
            
            # synonym for os.remove
            # be it file or dir symlink, we remove it like this
            os.unlink( path )
            
        except Exception as e:
            
            if 'Error 32' in str( e ):
                
                # file in use by another process
                
                HydrusData.DebugPrint( 'Trying to delete ' + path + ' failed because it was in use by another process.' )
                
            else:
                
                HydrusData.ShowText( 'Trying to delete ' + path + ' caused the following error:' )
                HydrusData.ShowException( e )
                
            
            return False
            
        
    else:
        
        path_stat = path_stat_nofollow
        
        if HC.PLATFORM_WINDOWS:
            
            # this can be needed on a Windows device
            TryToMakeFileWriteable( path, path_stat )
            
        
        try:
            
            if stat_is_dir( path_stat ):
                
                shutil.rmtree( path )
                
            else:
                
                os.remove( path )
                
            
        except Exception as e:
            
            if 'Error 32' in str( e ):
                
                # file in use by another process
                
                HydrusData.DebugPrint( 'Trying to delete ' + path + ' failed because it was in use by another process.' )
                
            else:
                
                HydrusData.ShowText( 'Trying to delete ' + path + ' caused the following error:' )
                HydrusData.ShowException( e )
                
            
            return False
            
        
    
    return True
    

def DestStatHasSameSizeAndDateAsSource( source_stat: os.stat_result, dest_stat: os.stat_result ):
    
    # this is a critical section of code so we moved it to just consider previously fetched stats. all the 'does dest exist?' stuff is implied by what you need to call this guy, hooray
    
    same_size = source_stat.st_size == dest_stat.st_size
    same_modified_time = int( source_stat.st_mtime ) == int( dest_stat.st_mtime )
    
    return same_size and same_modified_time
    

def DirectoryIsWriteable( path ):
    
    if not PotentialPathDeviceIsConnected( path ):
        
        raise Exception( f'Cannot figure out if "{path}" is writeable-to because its device does not seem to be mounted!' )
        
    
    try:
        
        MakeSureDirectoryExists( path )
        
    except ( PermissionError, OSError ) as e:
        
        return False
        
    
    if not os.path.exists( path ):
        
        # the makedirs failed, probably permission related
        return False
        
    
    if not os.access( path, os.W_OK | os.X_OK ):
        
        return False
        
    
    # we'll actually try making a file, since Windows Program Files passes the above test lmaoooo
    
    try:
        
        # also, using tempfile.TemporaryFile actually loops on PermissionError from Windows lmaaaooooo, thinking this is an already existing file
        # so, just do it manually!
        
        test_path = os.path.join( path, f'hpt_{os.urandom(12).hex()}.txt' )
        
        with open( test_path, 'wb' ) as f:
            
            f.write( b'Hydrus tested this directory for write permissions. If this file still exists, this directory can be written to but not deleted from.' )
            
        
        os.unlink( test_path )
        
    except:
        
        return False
        
    
    return True
    

def ElideSubdirsSafely( destination_directory: str, subdirs_elidable: str, path_character_limit: int | None, dirname_character_limit: int | None, force_ntfs_rules: bool ):
    
    if subdirs_elidable == '':
        
        return subdirs_elidable
        
    
    max_path_bytes = None
    max_path_characters = None
    
    if path_character_limit is None:
        
        if HC.PLATFORM_WINDOWS or force_ntfs_rules:
            
            max_path_characters = 260 # 256 + X:\...\
            
        elif HC.PLATFORM_LINUX:
            
            max_path_bytes = 4096
            
        elif HC.PLATFORM_MACOS:
            
            max_path_bytes = 1024
            
        else:
            
            max_path_bytes = 4096 # assume weird Linux but probably robust
            
        
    else:
        
        if HC.PLATFORM_WINDOWS or force_ntfs_rules:
            
            max_path_characters = path_character_limit
            
        else:
            
            max_path_bytes = path_character_limit
            
        
    
    max_dirname_characters = None
    max_dirname_bytes = None
    
    if dirname_character_limit is None:
        
        if HC.PLATFORM_WINDOWS or force_ntfs_rules:
            
            max_dirname_characters = 128
            
        else:
            
            max_dirname_bytes = 256
            
        
    else:
        
        if HC.PLATFORM_WINDOWS or force_ntfs_rules:
            
            max_dirname_characters = dirname_character_limit
            
        else:
            
            max_dirname_bytes = dirname_character_limit
            
        
    
    dirnames = subdirs_elidable.split( os.path.sep )
    
    actual_per_dirname_characters_limit = 64
    actual_per_dirname_bytes_limit = 256 - 10 # for some padding
    
    if HC.PLATFORM_WINDOWS or force_ntfs_rules:
        
        typical_filename_characters = int( max_path_characters / 4 )
        
        total_available_characters_left = max_path_characters - len( destination_directory ) - typical_filename_characters - len( dirnames ) - 10 # -10 for some padding
        
        actual_per_dirname_characters_limit = int( total_available_characters_left / len( dirnames ) )
        
        if actual_per_dirname_characters_limit < 4:
            
            raise Exception( 'Sorry, it looks like the combined export filename or directory would be too long! Try shortening the export directory name!' )
            
        
        if max_dirname_characters is not None:
            
            actual_per_dirname_characters_limit = min( actual_per_dirname_characters_limit, max_dirname_characters )
            
        
    else:
        
        typical_filename_bytes = int( max_path_bytes / 4 )
        
        total_available_bytes_left = max_path_bytes - len( destination_directory ) - typical_filename_bytes - len( dirnames ) - 10 # for some padding
        
        actual_per_dirname_bytes_limit = int( total_available_bytes_left / len( dirnames ) )
        
        if actual_per_dirname_bytes_limit < 4:
            
            raise Exception( 'Sorry, it looks like the combined export filename or directory would be too long! Try shortening the export directory name!' )
            
        
        if max_dirname_bytes is not None:
            
            actual_per_dirname_bytes_limit = min( actual_per_dirname_bytes_limit, max_dirname_bytes )
            
        
    
    dirnames_elided = []
    
    for dirname in dirnames:
        
        dirname = SanitizeFilename( dirname, force_ntfs_rules )
        
        if dirname == '':
            
            dirname = 'empty'
            
        
        def the_test( n ):
            
            if HC.PLATFORM_WINDOWS or force_ntfs_rules:
                
                # characters
                return len( n ) > actual_per_dirname_characters_limit
                
            else:
                
                # bytes
                return len( n.encode( 'utf-8' ) ) > actual_per_dirname_bytes_limit
                
            
        
        while the_test( dirname ):
            
            dirname = dirname[:-1]
            
            dirname = SanitizeFilename( dirname, force_ntfs_rules )
            
        
        dirname = dirname.strip()
        
        if dirname == '':
            
            dirname = 'truncated'
            
        
        dirnames_elided.append( dirname )
        
    
    return os.path.join( *dirnames_elided )
    

def ElideFilenameSafely( destination_directory: str, subdirs_elidable: str, base_filename: str, ext_suffix: str, path_character_limit: int | None, dirname_character_limit: int | None, filename_character_limit: int, force_ntfs_rules: bool ):
    
    # I could prefetch the GetFileSystemType of the dest directory here and test that precisely instead of PLATFORM...
    # but tbh that opens a Pandora's Box of 'NTFS mount on Linux', and sticking our finger in that sort of thing is Not A Good Idea. let the user handle that if and when it fails
    
    # most OSes cannot handle a filename or dirname with more than 256 X, where on Windows that is chars and Linux/macOS is bytes
    # Windows cannot handle a _total_ pathname more than 260 (unless you activate some new \\?\ thing that doesn't work great yet)
    # to be safe and deal with surprise extensions like (11) or .txt sidecars, we default to 220
    
    if base_filename == '':
        
        base_filename = 'empty'
        
    
    if len( subdirs_elidable ) > 0:
        
        subdirs_elided = ElideSubdirsSafely( destination_directory, subdirs_elidable, path_character_limit, dirname_character_limit, force_ntfs_rules )
        
        destination_directory = os.path.join( destination_directory, subdirs_elided )
        
    else:
        
        subdirs_elided = subdirs_elidable
        
    
    max_path_bytes = None
    max_path_characters = None
    
    if path_character_limit is None:
        
        if HC.PLATFORM_WINDOWS or force_ntfs_rules:
            
            max_path_characters = 260 # 256 + X:\...\
            
        elif HC.PLATFORM_LINUX:
            
            max_path_bytes = 4096
            
        elif HC.PLATFORM_MACOS:
            
            max_path_bytes = 1024
            
        else:
            
            max_path_bytes = 4096 # assume weird Linux but probably robust
            
        
    else:
        
        if HC.PLATFORM_WINDOWS or force_ntfs_rules:
            
            max_path_characters = path_character_limit
            
        else:
            
            max_path_bytes = path_character_limit
            
        
    
    if max_path_bytes is not None:
        
        max_path_bytes -= 20 # bit of padding
        
        max_bytes_with_full_filename = len( destination_directory.encode( 'utf-8' ) ) + 1 + filename_character_limit
        
        if max_bytes_with_full_filename > max_path_bytes:
            
            filename_character_limit -= max_bytes_with_full_filename - max_path_bytes
            
            min_filename_bytes = 18
            
            if filename_character_limit <= min_filename_bytes:
                
                raise Exception( 'Sorry, it looks like the combined export filename or directory would be too long! Try shortening the export directory name!' )
                
            
        
    
    if max_path_characters is not None:
        
        max_path_characters -= 10 # bit of padding
        
        max_characters_with_full_filename = len( destination_directory ) + 1 + filename_character_limit
        
        if max_characters_with_full_filename > max_path_characters:
            
            filename_character_limit -= max_characters_with_full_filename - max_path_characters
            
            min_filename_chars = 10
            
            if filename_character_limit <= min_filename_chars:
                
                raise Exception( 'Sorry, it looks like the combined export filename or directory would be too long! Try shortening the export directory name!' )
                
            
        
    
    if HC.PLATFORM_WINDOWS or force_ntfs_rules:
        
        filename_character_limit -= len( ext_suffix )
        
    else:
        
        filename_character_limit -= len( ext_suffix.encode( 'utf-8' ) )
        
    
    if filename_character_limit <= 0:
        
        raise Exception( 'Sorry, it looks like the export filename would be too long! Try shortening the export phrase or directory!' )
        
    
    def the_test( n ):
        
        if HC.PLATFORM_WINDOWS or force_ntfs_rules:
            
            return len( n ) > filename_character_limit
            
        else:
            
            return len( n.encode( 'utf-8' ) ) > filename_character_limit
            
        
    
    base_filename = SanitizeFilename( base_filename, force_ntfs_rules )
    
    while the_test( base_filename ):
        
        base_filename = base_filename[:-1]
        
        base_filename = SanitizeFilename( base_filename, force_ntfs_rules )
        
    
    base_filename = base_filename.strip()
    
    if base_filename == '':
        
        raise Exception( 'Sorry, it looks like the export filename would be too long! Try shortening the export phrase or directory!' )
        
    
    return ( subdirs_elided, base_filename )
    

def FigureOutDBDir( arg_db_dir: str ):
    
    switching_to_userpath_is_ok = False
    
    if arg_db_dir is None:
        
        if HC.RUNNING_FROM_MACOS_APP:
            
            if HC.USERPATH_DB_DIR is None:
                
                raise Exception( 'The userpath (for macOS App database) could not be determined!' )
                
            
            db_dir = HC.USERPATH_DB_DIR
            
        else:
            
            db_dir = HC.DEFAULT_DB_DIR
            
            switching_to_userpath_is_ok = True
            
        
    else:
        
        db_dir = arg_db_dir
        
        db_dir = ConvertPortablePathToAbsPath( db_dir, HC.BASE_DIR )
        
    
    if not DirectoryIsWriteable( db_dir ):
        
        if switching_to_userpath_is_ok:
            
            if HC.USERPATH_DB_DIR is None:
                
                raise Exception( f'The db path "{db_dir}" was not writeable-to, and the userpath could not be determined!' )
                
            else:
                
                if not DirectoryIsWriteable( HC.USERPATH_DB_DIR ):
                    
                    raise Exception( f'Neither the default db path "{db_dir}", nor the userpath fallback "{HC.USERPATH_DB_DIR}", were writeable-to!' )
                    
                
                HydrusData.Print( f'The given db path "{db_dir}" is not writeable-to! Falling back to userpath at "{HC.USERPATH_DB_DIR}".' )
                
                HC.WE_SWITCHED_TO_USERPATH = True
                
                db_dir = HC.USERPATH_DB_DIR
                
            
        else:
            
            raise Exception( f'The chosen db path "{db_dir}" is not writeable-to!' )
            
        
    
    return db_dir
    

def FileisWriteable( path: str ):
    
    # this is a sophisticated multi-plat method and cannot be replaced with a simple stat_result test
    return os.access( path, os.W_OK )
    

def FilterFreePaths( paths ):
    
    free_paths = []
    
    for path in paths:
        
        HydrusThreading.CheckIfThreadShuttingDown()
        
        if PathIsFree( path ):
            
            free_paths.append( path )
            
        
    
    return free_paths
    

def FilterOlderModifiedFiles( paths: collections.abc.Collection[ str ], grace_period: int ) -> list[ str ]:
    
    only_older_than = HydrusTime.GetNow() - grace_period
    
    good_paths = []
    
    for path in paths:
        
        try:
            
            if os.path.getmtime( path ) < only_older_than:
                
                good_paths.append( path )
                
            
        except:
            
            continue
            
        
    
    return good_paths
    

def GetDefaultLaunchPath():
    
    if HC.PLATFORM_WINDOWS:
        
        return 'windows is called directly'
        
    elif HC.PLATFORM_MACOS:
        
        return 'open "%path%"'
        
    elif HC.PLATFORM_LINUX:
        
        return 'xdg-open "%path%"'
        
    elif HC.PLATFORM_HAIKU:
        
        return 'open "%path%"'
        
    

# in truth this is 'sdiskpart', a namedtuple dynamic object def tucked inside psutil let's go
# this just teaches the linter what we are basically doing here
class FakeDiskPart( typing.Protocol ):
    
    device: str
    mountpoint: str
    fstype: str
    opts: str
    

@functools.lru_cache( maxsize = 128 )
def GetPartitionInfo( path ) -> FakeDiskPart | None:
    
    if not HydrusPSUtil.PSUTIL_OK:
        
        return None
        
    
    path = path.lower()
    
    try:
        
        for scan_network in ( False, True ):
            
            partition_infos = HydrusPSUtil.psutil.disk_partitions( all = scan_network )
            
            def sort_descending_mountpoint( partition_info ): # i.e. put '/home' before '/'
                
                return - len( partition_info.mountpoint )
                
            
            partition_infos.sort( key = sort_descending_mountpoint )
            
            for partition_info in partition_infos:
                
                if path.startswith( partition_info.mountpoint.lower() ):
                    
                    return partition_info
                    
                
            
        
    except UnicodeDecodeError: # wew lad psutil on some russian lad's fun filesystem
        
        return None
        
    
    return None
    

def GetDevice( path ) -> str | None:
    
    partition_info = GetPartitionInfo( path )
    
    if partition_info is None:
        
        return None
        
    else:
        
        # noinspection PyUnresolvedReferences
        return partition_info.device
        
    

def GetFileSystemType( path: str ) -> str | None:
    
    partition_info = GetPartitionInfo( path )
    
    if partition_info is None:
        
        return None
        
    else:
        
        # noinspection PyUnresolvedReferences
        return partition_info.fstype
        
    

def GetFreeSpace( path ) -> int | None:
    
    if not HydrusPSUtil.PSUTIL_OK:
        
        return None
        
    
    try:
        
        disk_usage = HydrusPSUtil.psutil.disk_usage( path )
        
        return disk_usage.free
        
    except:
        
        return None
        
    

def GetTotalSpace( path ) -> int | None:
    
    if not HydrusPSUtil.PSUTIL_OK:
        
        return None
        
    
    disk_usage = HydrusPSUtil.psutil.disk_usage( path )
    
    return disk_usage.total
    

def LaunchDirectory( path ):
    
    def do_it():
        
        if HC.PLATFORM_WINDOWS:
            
            os.startfile( path )
            
        else:
            
            if HC.PLATFORM_MACOS:
                
                cmd = [ 'open', path ]
                
            elif HC.PLATFORM_LINUX:
                
                cmd = [ 'xdg-open', path ]
                
            elif HC.PLATFORM_HAIKU:
                
                cmd = [ 'open', path ]
                
            else:
                
                raise NotImplementedError( 'Unknown platform!' )
                
            
            HydrusData.CheckProgramIsNotShuttingDown()
            
            HydrusSubprocess.RunSubprocess( cmd, this_is_a_potentially_long_lived_external_guy = True )
            
        
    
    thread = threading.Thread( target = do_it )
    
    thread.daemon = True
    
    thread.start()
    

def LaunchFile( path, launch_path = None ):
    
    def do_it( launch_path ):
        
        if HC.PLATFORM_WINDOWS and launch_path is None:
            
            os.startfile( path )
            
        else:
            
            if launch_path is None:
                
                launch_path = GetDefaultLaunchPath()
                
            
            complete_launch_path = launch_path.replace( '%path%', path )
            
            if HC.PLATFORM_WINDOWS:
                
                cmd = complete_launch_path
                
            else:
                
                cmd = shlex.split( complete_launch_path )
                
            
            if HG.subprocess_report_mode:
                
                message = 'Attempting to launch ' + path + ' using command ' + repr( cmd ) + '.'
                
                HydrusData.ShowText( message )
                
            
            try:
                
                HydrusData.CheckProgramIsNotShuttingDown()
                
                HydrusSubprocess.RunSubprocess( cmd, this_is_a_potentially_long_lived_external_guy = True, hide_terminal = False )
                
            except Exception as e:
                
                HydrusData.ShowText( 'Could not launch a file! Command used was:' + '\n' + str( cmd ) )
                
                HydrusData.ShowException( e )
                
            
        
    
    thread = threading.Thread( target = do_it, args = ( launch_path, ) )
    
    thread.daemon = True
    
    thread.start()
    

def MakeSureDirectoryExists( path ):
    
    if os.path.exists( path ):
        
        if os.path.isdir( path ):
            
            return
            
        else:
            
            raise Exception( f'Cannot create the directory "{path}" because it already exists as a normal file!' )
            
        
    else:
        
        try:
            
            os.makedirs( path, exist_ok = True )
            
        except FileNotFoundError as e:
            
            raise FileNotFoundError( f'While trying to ensure the directory "{path}" exists, none of the possible parent folders seem to exist either! Is the device not plugged in?' ) from e
            
        
    

def FileModifiedTimeIsOk( mtime: int | float ):
    
    if HC.PLATFORM_WINDOWS:
        
        # this is 1980-01-01 UTC, before which Windows can have trouble copying lmaoooooo
        # This is the 'DOS' epoch
        if mtime < 315532800:
            
            return False
            
        
    else:
        
        # Epoch obviously
        if mtime < 0:
            
            return False
            
        
    
    return True
    

def retry_blocking_io_call( func, *args, **kwargs ):
    
    NUM_ATTEMPTS = 5
    delay = 1.0
    
    for i in range( NUM_ATTEMPTS ):
        
        try:
            
            return func( *args, **kwargs )
            
        except BlockingIOError:
            
            if i < NUM_ATTEMPTS - 1:
                
                time.sleep( delay )
                
                delay *= 1.5
                
            else:
                
                raise
                
            
        
    

DO_NOT_DO_CHMOD_MODE = False

def CopyTimes( source, dest ):
    
    try:
        
        st = os.stat( source )
        
        os.utime( dest, ( st.st_atime, st.st_mtime ) )
        
        return True
        
    except:
        
        return False
        
    

def safe_copy2( source_path, dest_path ):
    
    mtime = os.path.getmtime( source_path )
    
    try_to_copy_modified_time = FileModifiedTimeIsOk( mtime )
    
    if DO_NOT_DO_CHMOD_MODE:
        
        retry_blocking_io_call( shutil.copyfile, source_path, dest_path )
        
        if try_to_copy_modified_time:
            
            retry_blocking_io_call( CopyTimes, source_path, dest_path )
            
        
    else:
        
        if try_to_copy_modified_time:
            
            try:
                
                # this overwrites on conflict without hassle
                retry_blocking_io_call( shutil.copy2, source_path, dest_path )
                
                return
                
            except PermissionError:
                
                try_to_copy_modified_time = False
                
            
        
        if not try_to_copy_modified_time:
            
            retry_blocking_io_call( shutil.copy, source_path, dest_path )
            
        
    

def safe_copystat( source_path, dest_path ):
    
    if DO_NOT_DO_CHMOD_MODE:
        
        retry_blocking_io_call( CopyTimes, source_path, dest_path )
        
    else:
        
        retry_blocking_io_call( shutil.copystat, source_path, dest_path )
        
    

def MergeFile( source, dest ) -> bool:
    """
    Moves a file unless it already exists with same size and modified date, in which case it simply deletes the source.
    
    :return: Whether an actual move happened.
    """
    
    try:
        
        source_stat = os.stat( source )
        
    except FileNotFoundError:
        
        raise Exception( f'Cannot file-merge "{source}" to "{dest}"--the source does not exist!' )
        
    
    if stat_is_dir( source_stat ):
        
        raise Exception( f'Cannot file-merge "{source}" to "{dest}"--the source is a directory, not a file!' )
        
    
    try:
        
        dest_stat = os.stat( dest )
        
    except FileNotFoundError:
        
        dest_stat = None
        
    
    if dest_stat is not None:
        
        # dest exists!
        
        if stat_is_dir( dest_stat ):
            
            raise Exception( f'Cannot file-merge "{source}" to "{dest}"--the destination is a directory, not a file!' )
            
        
        if stat_is_samefile( source_stat, dest_stat ):
            
            # one might think this should just return, but we don't want the parent caller deleting the source parent dir or anything, so we'll say responsibility for that situation is not here
            raise Exception( f'Woah, "{source}" and "{dest}" are the same file!' )
            
        
        if DestStatHasSameSizeAndDateAsSource( source_stat, dest_stat ):
            
            DeletePath( source )
            
            return False
            
        
        if HC.PLATFORM_WINDOWS:
            
            # this can be needed on a Windows device
            TryToMakeFileWriteable( dest, dest_stat )
            
        
    
    # this overwrites on conflict without hassle
    retry_blocking_io_call( shutil.move, source, dest, copy_function = safe_copy2 )
    
    return True
    

def MergeTree( source: str, dest: str, text_update_hook = None ):
    """
    Moves everything in the source to the dest using fast MergeFile tech.
    """
    
    try:
        
        source_stat = os.stat( source )
        
    except FileNotFoundError:
        
        raise Exception( f'Cannot directory-merge "{source}" to "{dest}"--the source does not exist!' )
        
    
    if stat_is_file( source_stat ):
        
        raise Exception( f'Cannot directory-merge "{source}" to "{dest}"--the source is a file, not a directory!' )
        
    
    try:
        
        dest_stat = os.stat( dest )
        
    except FileNotFoundError:
        
        dest_stat = None
        
    
    if dest_stat is not None:
        
        # dest exists!
        
        if stat_is_file( dest_stat ):
            
            raise Exception( f'Cannot directory-merge "{source}" to "{dest}"--the destination is a file, not a directory!' )
            
        
        if stat_is_samefile( source_stat, dest_stat ):
            
            # one might think this should just return, but we don't want the parent caller deleting the source parent dir or anything, so we'll say responsibility for that situation is not here
            raise Exception( f'Woah, "{source}" and "{dest}" are the same directory!' )
            
        
        # ok we have a populated dest, let's merge cleverly
        
        # I had a thing here that tried to optimise if dest existed but was empty, but it wasn't neat
        # also this guy used to do mergefile; now it does mirrorfile so as not to delete the source until the merge is done
        
        pauser = HydrusThreading.BigJobPauser()
        
        for ( root, dirnames, filenames ) in os.walk( source ):
            
            if text_update_hook is not None:
                
                text_update_hook( 'Copying ' + root + '.' )
                
            
            relative_path = os.path.relpath( root, source )
            dest_root = os.path.normpath( os.path.join( dest, relative_path ) )
            
            for dirname in dirnames:
                
                pauser.Pause()
                
                source_path = os.path.join( root, dirname )
                dest_path = os.path.join( dest_root, dirname )
                
                MakeSureDirectoryExists( dest_path )
                
                safe_copystat( source_path, dest_path )
                
            
            for filename in filenames:
                
                pauser.Pause()
                
                source_path = os.path.join( root, filename )
                dest_path = os.path.join( dest_root, filename )
                
                try:
                    
                    # not Merge; we only want to delete from source once we know everything worked out
                    MirrorFile( source_path, dest_path )
                    
                except Exception as e:
                    
                    raise Exception( f'While trying to merge "{source}" into the already-existing "{dest}", mirroring "{source_path}" to "{dest_path}" failed!' ) from e
                    
                
            
        
        DeletePath( source )
        
    else:
        
        # ok, nothing to merge, so simple move operation
        
        try:
            
            retry_blocking_io_call( shutil.move, source, dest, copy_function = safe_copy2 )
            
        except OSError:
            
            # if there were read only files in source and this was partition to partition, the copy2 goes ok but the subsequent source unlink fails
            # so, if it seems this has happened, let's just try a walking mergetree, which should be able to deal with these readonlies on a file-by-file basis
            if os.path.exists( dest ):
                
                MergeTree( source, dest, text_update_hook = text_update_hook )
                
            
        
    

def MirrorFile( source, dest ) -> bool:
    """
    Copies a file unless it already exists with same date and size.
    
    :return: Whether an actual file copy/overwrite happened.
    """
    
    try:
        
        source_stat = os.stat( source )
        
    except FileNotFoundError:
        
        raise Exception( f'Cannot file-mirror "{source}" to "{dest}"--the source does not exist!' )
        
    
    if stat_is_dir( source_stat ):
        
        raise Exception( f'Cannot file-mirror "{source}" to "{dest}"--the source is a directory, not a file!' )
        
    
    try:
        
        dest_stat = os.stat( dest )
        
    except FileNotFoundError:
        
        dest_stat = None
        
    
    if dest_stat is not None:
        
        # dest exists!
        
        if stat_is_dir( dest_stat ):
            
            raise Exception( f'Cannot file-mirror "{source}" to "{dest}"--the destination is a directory, not a file!' )
            
        
        if stat_is_samefile( source_stat, dest_stat ):
            
            return False
            
        
        if DestStatHasSameSizeAndDateAsSource( source_stat, dest_stat ):
            
            return False
            
        
        if HC.PLATFORM_WINDOWS:
            
            # this can be needed on a Windows device
            TryToMakeFileWriteable( dest, dest_stat )
            
        
    
    try:
        
        safe_copy2( source, dest )
        
    except Exception as e:
        
        from hydrus.core import HydrusTemp
        
        if isinstance( e, OSError ) and 'Errno 28' in str( e ) and dest.startswith( HydrusTemp.GetCurrentTempDir() ):
            
            message = 'The recent failed file copy looks like it was because your temporary folder ran out of disk space!'
            message += '\n' * 2
            message += 'This folder is normally on your system drive, so either free up space on that or use the "--temp_dir" launch command to tell hydrus to use a different location for the temporary folder. (Check the advanced help for more info!)'
            message += '\n' * 2
            message += 'If your system drive appears to have space but your temp folder still maxed out, then there are probably special rules about how big a file we are allowed to put in there. Use --temp_dir.'
            
            if HC.PLATFORM_LINUX:
                
                message += ' You are also on Linux, where these temp dir rules are not uncommon!'
                
            
            HydrusData.ShowText( message )
            
        
        raise
        
    
    return True
    

def MirrorTree( source: str, dest: str, text_update_hook = None, is_cancelled_hook = None ):
    """
    Makes the destination directory look exactly like the source using fast MirrorFile tech.
    It deletes surplus stuff in the dest!
    """
    
    try:
        
        source_stat = os.stat( source )
        
    except FileNotFoundError:
        
        raise Exception( f'Cannot directory-mirror "{source}" to "{dest}"--the source does not exist!' )
        
    
    if stat_is_file( source_stat ):
        
        raise Exception( f'Cannot directory-mirror "{source}" to "{dest}"--the source is a file, not a directory!' )
        
    
    try:
        
        dest_stat = os.stat( dest )
        
    except FileNotFoundError:
        
        dest_stat = None
        
    
    if dest_stat is not None:
        
        # dest exists!
        
        if stat_is_file( dest_stat ):
            
            raise Exception( f'Cannot directory-mirror "{source}" to "{dest}"--the destination is a file, not a directory!' )
            
        
        if stat_is_samefile( source_stat, dest_stat ):
            
            return
            
        
    
    pauser = HydrusThreading.BigJobPauser()
    
    MakeSureDirectoryExists( dest )
    
    deletee_paths = set()
    
    for ( root, dirnames, filenames ) in os.walk( source ):
        
        if is_cancelled_hook is not None and is_cancelled_hook():
            
            return
            
        
        if text_update_hook is not None:
            
            text_update_hook( 'Copying ' + root + '.' )
            
        
        relative_path = os.path.relpath( root, source )
        dest_root = os.path.normpath( os.path.join( dest, relative_path ) )
        
        surplus_dest_paths = { os.path.join( dest_root, dest_filename ) for dest_filename in os.listdir( dest_root ) }
        
        for dirname in dirnames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, dirname )
            dest_path = os.path.join( dest_root, dirname )
            
            surplus_dest_paths.discard( dest_path )
            
            MakeSureDirectoryExists( dest_path )
            
            safe_copystat( source_path, dest_path )
            
        
        for filename in filenames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, filename )
            
            dest_path = os.path.join( dest_root, filename )
            
            surplus_dest_paths.discard( dest_path )
            
            try:
                
                MirrorFile( source_path, dest_path )
                
            except Exception as e:
                
                raise Exception( f'While trying to mirror "{source}" into "{dest}", copying "{source_path}" to "{dest_path}" failed!' ) from e
                
            
        
        deletee_paths.update( surplus_dest_paths )
        
    
    for deletee_path in deletee_paths:
        
        pauser.Pause()
        
        DeletePath( deletee_path )
        
    

def OpenFileLocation( path ):
    
    def do_it():
        
        if HC.PLATFORM_WINDOWS:
            
            cmd = [ 'explorer', '/select,', path ]
            
        elif HC.PLATFORM_MACOS:
            
            cmd = [ 'open', '-R', path ]
            
        elif HC.PLATFORM_LINUX:
            
            raise NotImplementedError( 'Linux cannot open file locations!' )
            
        elif HC.PLATFORM_HAIKU:
            
            raise NotImplementedError( 'Haiku cannot open file locations!' )
            
        else:
            
            raise NotImplementedError( 'Unknown platform!' )
            
        
        HydrusData.CheckProgramIsNotShuttingDown()
        
        HydrusSubprocess.RunSubprocess( cmd, this_is_a_potentially_long_lived_external_guy = True )
        
    
    thread = threading.Thread( target = do_it )
    
    thread.daemon = True
    
    thread.start()
    

def PathIsFree( path ):
    
    if not os.path.exists( path ):
        
        return False
        
    
    try:
        
        stat_result = os.stat( path )
        
        current_bits = stat_result.st_mode
        
        if current_bits & stat.S_IWRITE:
            
            os.rename( path, path ) # rename a path to itself
            
            return True
            
        
    except OSError as e: # 'already in use by another process' or an odd filename too long error
        
        HydrusData.Print( 'Already in use/inaccessible: ' + path )
        
        return False
        
    
    try:
        
        with open( path, 'rb' ) as f:
            
            return True
            
        
    except:
        
        HydrusData.Print( 'Could not open the file: ' + path )
        
        return False
        
    

def PotentialPathDeviceIsConnected( path: str ):
    
    # this is a little hacky, but it works at catching "H:\ is not plugged in"
    # does not work for Linux, oh well
    try:
        
        os.path.ismount( path )
        
        return True
        
    except FileNotFoundError:
        
        return False
        
    

def ReadFileLikeAsBlocks( f ) -> collections.abc.Iterator[ bytes ]:
    
    next_block = f.read( HC.READ_BLOCK_SIZE )
    
    while len( next_block ) > 0:
        
        yield next_block
        
        next_block = f.read( HC.READ_BLOCK_SIZE )
        
    

def RecyclePath( path ):
    
    if HG.file_report_mode:
        
        HydrusData.ShowText( 'Recycling {}'.format( path ) )
        
        HydrusData.ShowText( ''.join( traceback.format_stack() ) )
        
    
    MAX_NUM_ATTEMPTS = 3
    
    try:
        
        path_stat_nofollow = os.stat( path, follow_symlinks = False ) # this is the stat on the path as-is. if it is a symlink, we looking at it, not where it points
        
    except FileNotFoundError:
        
        return
        
    
    # we don't care if this is a link or a file; send2trash just deletes the link if it is one
    
    if HC.PLATFORM_WINDOWS:
        
        # this can be needed on a Windows device
        TryToMakeFileWriteable( path, path_stat_nofollow )
        
    
    for i in range( MAX_NUM_ATTEMPTS ):
        
        try:
            
            send2trash.send2trash( path )
            
        except Exception as e:
            
            if getattr( e, 'winerror', None ) == -2144927711: # 0x80270021, mystery error that can be for many things but could be about sharing violation parallel access blah or megalag from a huge trash
                
                if i < MAX_NUM_ATTEMPTS - 1:
                    
                    time.sleep( 0.5 )
                    
                    continue
                    
                else:
                    
                    HydrusData.Print( f'I keep getting the 0x80270021 error when trying to recycle "{path}"!' )
                    
                    HydrusData.PrintException( e, do_wait = False )
                    
                
            elif isinstance( e, OSError ) and 'Errno 36' in str( e ):
                
                HydrusData.Print( f'Could not recycle "{path}" because a filename would be too long! (maybe Linux .trashinfo?)' )
                
            else:
                
                HydrusData.Print( f'Trying to recycle "{path}" created this error:' )
                
                HydrusData.PrintException( e, do_wait = False )
                
            
            HydrusData.Print( 'I will fully delete it instead.' )
            
            DeletePath( path )
            
        
        break
        
    

NTFS_disallowed_names_case_insensitive = { 'con', 'prn', 'aux', 'nul' }
NTFS_disallowed_names_case_insensitive.update( ( f'com{x}' for x in range( 1, 10 ) ) )
NTFS_disallowed_names_case_insensitive.update( ( f'lpt{x}' for x in range( 1, 10 ) ) )

def SanitizeFilename( filename: str, force_ntfs_rules: bool ) -> str:
    
    if HC.PLATFORM_WINDOWS or force_ntfs_rules:
        
        # \, /, :, *, ?, ", <, >, |
        bad_characters = r'[\\/:*?"<>|]'
        
        disallowed_names_case_insensitive = NTFS_disallowed_names_case_insensitive
        disallowed_suffix_characters = { '.', ' ' }
        
    else:
        
        bad_characters = '/'
        
        disallowed_names_case_insensitive = set()
        disallowed_suffix_characters = {}
        
    
    clean_filename = re.sub( bad_characters, '_', filename )
    
    if len( disallowed_suffix_characters ) > 0:
        
        while True in ( clean_filename.endswith( c ) for c in disallowed_suffix_characters ):
            
            clean_filename = clean_filename[:-1]
            
        
    
    clean_filename = clean_filename.strip()
    
    if len( disallowed_names_case_insensitive ) > 0:
        
        while clean_filename.lower() in disallowed_names_case_insensitive:
            
            clean_filename = clean_filename[:-1]
            
        
    
    return clean_filename
    

try:
    
    PROCESS_UMASK = os.umask( 0o022 )
    os.umask( PROCESS_UMASK )
    
except:
    
    PROCESS_UMASK = 0o022
    

def TryToGiveFileNicePermissionBits( path ):
    
    if DO_NOT_DO_CHMOD_MODE:
        
        return
        
    
    if not os.path.exists( path ):
        
        return
        
    
    try:
        
        stat_result = os.stat( path )
        
        current_bits = stat_result.st_mode
        
        if HC.PLATFORM_WINDOWS:
            
            # this is actually the same value as S_IWUSR, but let's not try to second guess ourselves
            desired_bits = stat.S_IREAD | stat.S_IWRITE
            
        else:
            
            # typically guarantee 644 for regular files m8, but now we also take umask into account
            
            desired_bits = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH ) & ~PROCESS_UMASK
            
        
        if not ( desired_bits & current_bits ) == desired_bits:
            
            os.chmod( path, current_bits | desired_bits )
            
        
    except Exception as e:
        
        HydrusData.Print( 'Wanted to add read and write permission to "{}", but had an error: {}'.format( path, str( e ) ) )
        
    

def TryToMakeFileWriteable( path: str, path_stat: os.stat_result ):
    
    if DO_NOT_DO_CHMOD_MODE:
        
        return
        
    
    if FileisWriteable( path ):
        
        return
        
    
    try:
        
        current_bits = path_stat.st_mode
        
        if HC.PLATFORM_WINDOWS:
            
            # this is actually the same value as S_IWUSR, but let's not try to second-guess ourselves
            desired_bits = stat.S_IREAD | stat.S_IWRITE
            
        else:
            
            # this only does what we want if we own the file, but only owners can non-sudo change permission anyway
            desired_bits = stat.S_IWUSR
            
        
        if not ( desired_bits & current_bits ) == desired_bits:
            
            os.chmod( path, current_bits | desired_bits )
            
        
    except Exception as e:
        
        HydrusData.Print( 'Wanted to add user write permission to "{}", but had an error: {}'.format( path, str( e ) ) )
        
    
