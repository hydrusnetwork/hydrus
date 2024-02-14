import collections
import functools
import os
import typing

import psutil
import re
import send2trash
import shlex
import shutil
import stat
import subprocess
import threading
import traceback

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusThreading
from hydrus.core import HydrusTime

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
        
    
    if not HC.PLATFORM_WINDOWS and not os.path.exists( abs_path ):
        
        abs_path = abs_path.replace( '\\', '/' )
        
    
    return abs_path
    

def CopyFileLikeToFileLike( f_source, f_dest ):
    
    for block in ReadFileLikeAsBlocks( f_source ): f_dest.write( block )
    

def DeletePath( path ) -> bool:
    
    if HG.file_report_mode:
        
        HydrusData.ShowText( 'Deleting {}'.format( path ) )
        
        HydrusData.ShowText( ''.join( traceback.format_stack() ) )
        
    
    if os.path.lexists( path ):
        
        TryToMakeFileWriteable( path )
        
        try:
            
            if os.path.isdir( path ):
                
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
        
        test_path = os.path.join( path, 'hydrus_permission_test' )
        
        with open( test_path, 'wb' ) as f:
            
            f.write( b'If this file still exists, this directory can be written to but not deleted from.' )
            
        
        os.unlink( test_path )
        
    except:
        
        return False
        
    
    return True
    

def ElideFilenameOrDirectorySafely( name: str, num_characters_used_in_other_components: typing.Optional[ int ] = None, num_characters_already_used_in_this_component: typing.Optional[ int ] = None ):
    
    # most OSes cannot handle a filename or dirname with more than 255 characters
    # Windows cannot handle a _total_ pathname more than 260
    # to be safe and deal with surprise extensions like (11) or .txt sidecars, we use 220
    # moreover, unicode paths are encoded to bytes, so we have to count differently
    
    MAX_PATH_LENGTH = 220
    
    num_characters_available = MAX_PATH_LENGTH
    
    if num_characters_used_in_other_components is not None:
        
        if HC.PLATFORM_WINDOWS:
            
            num_characters_available -= num_characters_used_in_other_components
            
            if num_characters_available <= 0:
                
                raise Exception( 'Sorry, it looks like the combined export filename or directory would be too long! Try shortening the export directory name!' )
                
            
        
    
    if num_characters_already_used_in_this_component is not None:
        
        num_characters_available -= num_characters_already_used_in_this_component
        
        if num_characters_available <= 0:
            
            raise Exception( 'Sorry, it looks like the export filename would be too long! Try shortening the export phrase or directory!' )
            
        
    
    if name == '':
        
        return name
        
    
    while len( name.encode( 'utf-8' ) ) > num_characters_available:
        
        name = name[:-1]
        
    
    if name == '':
        
        raise Exception( 'Sorry, it looks like the export filename would be too long! Try shortening the export phrase or directory!' )
        
    
    return name
    

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
    
    return os.access( path, os.W_OK )
    

def FilterFreePaths( paths ):
    
    free_paths = []
    
    for path in paths:
        
        HydrusThreading.CheckIfThreadShuttingDown()
        
        if PathIsFree( path ):
            
            free_paths.append( path )
            
        
    
    return free_paths
    

def FilterOlderModifiedFiles( paths: typing.Collection[ str ], grace_period: int ) -> typing.List[ str ]:
    
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
        
    

@functools.lru_cache( maxsize = 128 )
def GetPartitionInfo( path ) -> typing.Optional[ typing.NamedTuple ]:
    
    path = path.lower()
    
    try:
        
        for scan_network in ( False, True ):
            
            partition_infos = psutil.disk_partitions( all = scan_network )
            
            def sort_descending_mountpoint( partition_info ): # i.e. put '/home' before '/'
                
                return - len( partition_info.mountpoint )
                
            
            partition_infos.sort( key = sort_descending_mountpoint )
            
            for partition_info in partition_infos:
                
                if path.startswith( partition_info.mountpoint.lower() ):
                    
                    return partition_info
                    
                
            
        
    except UnicodeDecodeError: # wew lad psutil on some russian lad's fun filesystem
        
        return None
        
    
    return None
    

def GetDevice( path ) -> typing.Optional[ str ]:
    
    partition_info = GetPartitionInfo( path )
    
    if partition_info is None:
        
        return None
        
    else:
        
        return partition_info.device
        
    

def GetFileSystemType( path: str ) -> typing.Optional[ str ]:
    
    partition_info = GetPartitionInfo( path )
    
    if partition_info is None:
        
        return None
        
    else:
        
        return partition_info.fstype
        
    

def GetFreeSpace( path ):
    
    disk_usage = psutil.disk_usage( path )
    
    return disk_usage.free
    

def GetTotalSpace( path ):
    
    disk_usage = psutil.disk_usage( path )
    
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
                
            
            # setsid call un-childs this new process
            
            sbp_kwargs = HydrusData.GetSubprocessKWArgs()
            
            preexec_fn = getattr( os, 'setsid', None )
            
            HydrusData.CheckProgramIsNotShuttingDown()
            
            process = subprocess.Popen( cmd, preexec_fn = preexec_fn, **sbp_kwargs )
            
            HydrusThreading.SubprocessCommunicate( process )
            
        
    
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
            
            hide_terminal = False
            
            if HC.PLATFORM_WINDOWS:
                
                cmd = complete_launch_path
                
                preexec_fn = None
                
            else:
                
                cmd = shlex.split( complete_launch_path )
                
                preexec_fn = getattr( os, 'setsid', None )
                
            
            if HG.subprocess_report_mode:
                
                message = 'Attempting to launch ' + path + ' using command ' + repr( cmd ) + '.'
                
                HydrusData.ShowText( message )
                
            
            try:
                
                sbp_kwargs = HydrusData.GetSubprocessKWArgs( hide_terminal = hide_terminal, text = True )
                
                HydrusData.CheckProgramIsNotShuttingDown()
                
                process = subprocess.Popen( cmd, preexec_fn = preexec_fn, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
                
                ( stdout, stderr ) = HydrusThreading.SubprocessCommunicate( process )
                
                if HG.subprocess_report_mode:
                    
                    if stdout is None and stderr is None:
                        
                        HydrusData.ShowText( 'No stdout or stderr came back.' )
                        
                    
                    if stdout is not None:
                        
                        HydrusData.ShowText( 'stdout: ' + repr( stdout ) )
                        
                    
                    if stderr is not None:
                        
                        HydrusData.ShowText( 'stderr: ' + repr( stderr ) )
                        
                    
                
            except Exception as e:
                
                HydrusData.ShowText( 'Could not launch a file! Command used was:' + os.linesep + str( cmd ) )
                
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
            
        
    

def FileModifiedTimeIsOk( mtime: typing.Union[ int, float ] ):
    
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
    

def safe_copy2( source, dest ):
    
    mtime = os.path.getmtime( source )
    
    if FileModifiedTimeIsOk( mtime ):
        
        try:
            
            # this overwrites on conflict without hassle
            shutil.copy2( source, dest )
            
        except PermissionError:
            
            HydrusData.Print( f'Failed to copy2 metadata from {source} to {dest}! mtime was {HydrusTime.TimestampToPrettyTime( mtime )}' )
            
            shutil.copy( source, dest )
            
        
    else:
        
        shutil.copy( source, dest )
        
    

def MergeFile( source, dest ) -> bool:
    """
    Moves a file unless it already exists with same size and modified date, in which case it simply deletes the source.
    
    :return: Whether an actual move happened.
    """
    
    if not os.path.exists( source ):
        
        raise Exception( f'Cannot file-merge "{source}" to "{dest}"--the source does not exist!' )
        
    
    if os.path.isdir( source ):
        
        raise Exception( f'Cannot file-merge "{source}" to "{dest}"--the source is a directory, not a file!' )
        
    
    if os.path.isdir( dest ):
        
        raise Exception( f'Cannot file-merge "{source}" to "{dest}"--the destination is a directory, not a file!' )
        
    
    if os.path.exists( source ) and os.path.exists( dest ) and os.path.samefile( source, dest ):
        
        # maybe this should just return, but we don't want the parent caller deleting the source or anything, so bleh
        raise Exception( f'Woah, "{source}" and "{dest}" are the same file!' )
        
    
    if PathsHaveSameSizeAndDate( source, dest ):
        
        DeletePath( source )
        
        return False
        
    
    # this overwrites on conflict without hassle
    shutil.move( source, dest, copy_function = safe_copy2 )
    
    return True
    

def MergeTree( source, dest, text_update_hook = None ):
    """
    Moves everything in the source to the dest using fast MergeFile tech.
    """
    
    if not os.path.exists( source ):
        
        raise Exception( f'Cannot directory-merge "{source}" to "{dest}"--the source does not exist!' )
        
    
    if os.path.isfile( source ):
        
        raise Exception( f'Cannot directory-merge "{source}" to "{dest}"--the source is a file, not a directory!' )
        
    
    if os.path.isfile( dest ):
        
        raise Exception( f'Cannot directory-merge "{source}" to "{dest}"--the destination is a file, not a directory!' )
        
    
    if os.path.exists( source ) and os.path.exists( dest ) and os.path.samefile( source, dest ):
        
        # maybe this should just return, but we don't want the parent caller deleting the source or anything, so bleh
        raise Exception( f'Woah, "{source}" and "{dest}" are the same directory!' )
        
    
    pauser = HydrusThreading.BigJobPauser()
    
    if not os.path.exists( dest ):
        
        try:
            
            shutil.move( source, dest, copy_function = safe_copy2 )
            
        except OSError:
            
            # if there were read only files in source and this was partition to partition, the copy2 goes ok but the subsequent source unlink fails
            # so, if it seems this has happened, let's just try a walking mergetree, which should be able to deal with these readonlies on a file-by-file basis
            if os.path.exists( dest ):
                
                MergeTree( source, dest, text_update_hook = text_update_hook )
                
            
        
    else:
        
        # I had a thing here that tried to optimise if dest existed but was empty, but it wasn't neat
        
        for ( root, dirnames, filenames ) in os.walk( source ):
            
            if text_update_hook is not None:
                
                text_update_hook( 'Copying ' + root + '.' )
                
            
            dest_root = root.replace( source, dest )
            
            for dirname in dirnames:
                
                pauser.Pause()
                
                source_path = os.path.join( root, dirname )
                dest_path = os.path.join( dest_root, dirname )
                
                MakeSureDirectoryExists( dest_path )
                
                shutil.copystat( source_path, dest_path )
                
            
            for filename in filenames:
                
                pauser.Pause()
                
                source_path = os.path.join( root, filename )
                dest_path = os.path.join( dest_root, filename )
                
                try:
                    
                    MergeFile( source_path, dest_path )
                    
                except Exception as e:
                    
                    raise Exception( f'While trying to merge "{source}" into the already-existing "{dest}", moving "{source_path}" to "{dest_path}" failed!' ) from e
                    
                
            
        
        DeletePath( source )
        
    

def MirrorFile( source, dest ) -> bool:
    """
    Copies a file unless it already exists with same date and size.
    
    :return: Whether an actual file copy/overwrite happened.
    """
    
    if not os.path.exists( source ):
        
        raise Exception( f'Cannot file-mirror "{source}" to "{dest}"--the source does not exist!' )
        
    
    if os.path.isdir( source ):
        
        raise Exception( f'Cannot file-mirror "{source}" to "{dest}"--the source is a directory, not a file!' )
        
    
    if os.path.isdir( dest ):
        
        raise Exception( f'Cannot file-mirror "{source}" to "{dest}"--the destination is a directory, not a file!' )
        
    
    if os.path.exists( source ) and os.path.exists( dest ) and os.path.samefile( source, dest ):
        
        return False
        
    
    if PathsHaveSameSizeAndDate( source, dest ):
        
        return False
        
    else:
        
        try:
            
            TryToMakeFileWriteable( dest )
            
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
        
    

def MirrorTree( source, dest, text_update_hook = None, is_cancelled_hook = None ):
    """
    Makes the destination directory look exactly like the source using fast MirrorFile tech.
    It deletes surplus stuff in the dest!
    """
    
    if not os.path.exists( source ):
        
        raise Exception( f'Cannot directory-mirror "{source}" to "{dest}"--the source does not exist!' )
        
    
    if os.path.isfile( source ):
        
        raise Exception( f'Cannot directory-mirror "{source}" to "{dest}"--the source is a file, not a directory!' )
        
    
    if os.path.isfile( dest ):
        
        raise Exception( f'Cannot directory-mirror "{source}" to "{dest}"--the destination is a file, not a directory!' )
        
    
    if os.path.exists( source ) and os.path.exists( dest ) and os.path.samefile( source, dest ):
        
        return
        
    
    pauser = HydrusThreading.BigJobPauser()
    
    MakeSureDirectoryExists( dest )
    
    for ( root, dirnames, filenames ) in os.walk( source ):
        
        if is_cancelled_hook is not None and is_cancelled_hook():
            
            return
            
        
        if text_update_hook is not None:
            
            text_update_hook( 'Copying ' + root + '.' )
            
        
        dest_root = root.replace( source, dest )
        
        surplus_dest_paths = { os.path.join( dest_root, dest_filename ) for dest_filename in os.listdir( dest_root ) }
        
        for dirname in dirnames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, dirname )
            dest_path = os.path.join( dest_root, dirname )
            
            surplus_dest_paths.discard( dest_path )
            
            MakeSureDirectoryExists( dest_path )
            
            shutil.copystat( source_path, dest_path )
            
        
        for filename in filenames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, filename )
            
            dest_path = os.path.join( dest_root, filename )
            
            surplus_dest_paths.discard( dest_path )
            
            try:
                
                MirrorFile( source_path, dest_path )
                
            except Exception as e:
                
                raise Exception( f'While trying to mirror "{source}" into "{dest}", moving "{source_path}" to "{dest_path}" failed!' ) from e
                
            
        
        for dest_path in surplus_dest_paths:
            
            pauser.Pause()
            
            DeletePath( dest_path )
            
        
    

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
            
        
        sbp_kwargs = HydrusData.GetSubprocessKWArgs( hide_terminal = False )
        
        HydrusData.CheckProgramIsNotShuttingDown()
        
        process = subprocess.Popen( cmd, **sbp_kwargs )
        
        HydrusThreading.SubprocessCommunicate( process )
        
    
    thread = threading.Thread( target = do_it )
    
    thread.daemon = True
    
    thread.start()
    
def PathsHaveSameSizeAndDate( path1, path2 ):
    
    if os.path.exists( path1 ) and os.path.exists( path2 ):
        
        same_size = os.path.getsize( path1 ) == os.path.getsize( path2 )
        same_modified_time = int( os.path.getmtime( path1 ) ) == int( os.path.getmtime( path2 ) )
        
        if same_size and same_modified_time:
            
            return True
            
        
    
    return False
    
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
        
    

def ReadFileLikeAsBlocks( f ):
    
    next_block = f.read( HC.READ_BLOCK_SIZE )
    
    while len( next_block ) > 0:
        
        yield next_block
        
        next_block = f.read( HC.READ_BLOCK_SIZE )
        
    
def RecyclePath( path ):
    
    if HG.file_report_mode:
        
        HydrusData.ShowText( 'Recycling {}'.format( path ) )
        
        HydrusData.ShowText( ''.join( traceback.format_stack() ) )
        
    
    if os.path.lexists( path ):
        
        TryToMakeFileWriteable( path )
        
        try:
            
            send2trash.send2trash( path )
            
        except:
            
            HydrusData.Print( 'Trying to recycle ' + path + ' created this error:' )
            
            HydrusData.DebugPrint( traceback.format_exc() )
            
            HydrusData.Print( 'It has been fully deleted instead.' )
            
            DeletePath( path )
            
        
    
def SanitizeFilename( filename, force_ntfs = False ) -> str:
    
    if HC.PLATFORM_WINDOWS or force_ntfs:
        
        # \, /, :, *, ?, ", <, >, |
        bad_characters = r'[\\/:*?"<>|]'
        
    else:
        
        bad_characters = '/'
        
    
    return re.sub( bad_characters, '_', filename )
    

def SanitizePathForExport( directory_path, directories_and_filename ):
    
    # this does not figure out the situation where the suffix directories cross a mount point to a new file system, but at that point it is user's job to fix
    
    components = directories_and_filename.split( os.path.sep )
    
    filename = components[-1]
    
    suffix_directories = components[:-1]
    
    fst = GetFileSystemType( directory_path )
    
    if fst is None:
        
        force_ntfs = False
        
    else:
        
        force_ntfs = fst.lower() in ( 'ntfs', 'exfat' )
        
    
    suffix_directories = [ SanitizeFilename( suffix_directory, force_ntfs = force_ntfs ) for suffix_directory in suffix_directories ]
    filename = SanitizeFilename( filename, force_ntfs = force_ntfs )
    
    sanitized_components = suffix_directories
    sanitized_components.append( filename )
    
    return os.path.join( *sanitized_components )
    

def TryToGiveFileNicePermissionBits( path ):
    
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
            
            try:
                
                umask = os.umask( 0o022 )
                os.umask( umask )
                
            except:
                
                umask = 0o022
                
            
            desired_bits = ( stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH ) & ~umask
            
        
        if not ( desired_bits & current_bits ) == desired_bits:
            
            os.chmod( path, current_bits | desired_bits )
            
        
    except Exception as e:
        
        HydrusData.Print( 'Wanted to add read and write permission to "{}", but had an error: {}'.format( path, str( e ) ) )
        
    
def TryToMakeFileWriteable( path ):
    
    if not os.path.exists( path ):
        
        return
        
    
    if FileisWriteable( path ):
        
        return
        
    
    try:
        
        stat_result = os.stat( path )
        
        current_bits = stat_result.st_mode
        
        if HC.PLATFORM_WINDOWS:
            
            # this is actually the same value as S_IWUSR, but let's not try to second guess ourselves
            desired_bits = stat.S_IREAD | stat.S_IWRITE
            
        else:
            
            # this only does what we want if we own the file, but only owners can non-sudo change permission anyway
            desired_bits = stat.S_IWUSR
            
        
        if not ( desired_bits & current_bits ) == desired_bits:
            
            os.chmod( path, current_bits | desired_bits )
            
        
    except Exception as e:
        
        HydrusData.Print( 'Wanted to add user write permission to "{}", but had an error: {}'.format( path, str( e ) ) )
        
    
