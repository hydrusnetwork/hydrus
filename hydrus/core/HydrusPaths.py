import collections
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

mimes_to_default_thumbnail_paths = collections.defaultdict( lambda: os.path.join( HC.STATIC_DIR, 'hydrus.png' ) )

mimes_to_default_thumbnail_paths[ HC.APPLICATION_PDF ] = os.path.join( HC.STATIC_DIR, 'pdf.png' )
mimes_to_default_thumbnail_paths[ HC.APPLICATION_PSD ] = os.path.join( HC.STATIC_DIR, 'psd.png' )
mimes_to_default_thumbnail_paths[ HC.APPLICATION_CLIP ] = os.path.join( HC.STATIC_DIR, 'clip.png' )

for mime in HC.AUDIO:
    
    path = os.path.join( HC.STATIC_DIR, 'audio.png' )
    
    mimes_to_default_thumbnail_paths[ mime ] = os.path.join( path )
    

for mime in HC.VIDEO:
    
    path = os.path.join( HC.STATIC_DIR, 'video.png' )
    
    mimes_to_default_thumbnail_paths[ mime ] = os.path.join( path )
    

for mime in HC.ARCHIVES:
    
    path = os.path.join( HC.STATIC_DIR, 'zip.png' )
    
    mimes_to_default_thumbnail_paths[ mime ] = os.path.join( path )
    

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
    
def CopyAndMergeTree( source, dest ):
    
    pauser = HydrusData.BigJobPauser()
    
    MakeSureDirectoryExists( dest )
    
    num_errors = 0
    
    for ( root, dirnames, filenames ) in os.walk( source ):
        
        dest_root = root.replace( source, dest )
        
        for dirname in dirnames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, dirname )
            dest_path = os.path.join( dest_root, dirname )
            
            MakeSureDirectoryExists( dest_path )
            
            shutil.copystat( source_path, dest_path )
            
        
        for filename in filenames:
            
            if num_errors > 5:
                
                raise Exception( 'Too many errors, directory copy abandoned.' )
                
            
            pauser.Pause()
            
            source_path = os.path.join( root, filename )
            dest_path = os.path.join( dest_root, filename )
            
            ok = MirrorFile( source_path, dest_path )
            
            if not ok:
                
                num_errors += 1
                
            
        
    
def CopyFileLikeToFileLike( f_source, f_dest ):
    
    for block in ReadFileLikeAsBlocks( f_source ): f_dest.write( block )
    
def DeletePath( path ):
    
    if HG.file_report_mode:
        
        HydrusData.ShowText( 'Deleting {}'.format( path ) )
        
        HydrusData.ShowText( ''.join( traceback.format_stack() ) )
        
    
    if os.path.exists( path ):
        
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
                
            
        
    
def DirectoryIsWriteable( path ):
    
    while not os.path.exists( path ):
        
        try:
            
            path = os.path.dirname( path )
            
        except:
            
            return False
            
        
    
    if not os.access( path, os.W_OK | os.X_OK ):
        
        return False
        
    
    # we'll actually do a file, since Program Files passes the above test lmaoooo
    
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
    
def FileisWriteable( path: str ):
    
    return os.access( path, os.W_OK )
    
def FilterFreePaths( paths ):
    
    free_paths = []
    
    for path in paths:
        
        HydrusThreading.CheckIfThreadShuttingDown()
        
        if PathIsFree( path ):
            
            free_paths.append( path )
            
        
    
    return free_paths
    
def GetDefaultLaunchPath():
    
    if HC.PLATFORM_WINDOWS:
        
        return 'windows is called directly'
        
    elif HC.PLATFORM_MACOS:
        
        return 'open "%path%"'
        
    elif HC.PLATFORM_LINUX:
        
        return 'xdg-open "%path%"'
        
    elif HC.PLATFORM_HAIKU:
        
        return 'open "%path%"'
        
    
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
        
    

def GetFileSystemType( path ):
    
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
    
    it_exists_already = os.path.exists( path )
    
    if it_exists_already:
        
        if os.path.isdir( path ):
            
            return
            
        else:
            
            raise Exception( 'Sorry, the desired directory "{}" already exists as a normal file!'.format( path ) )
            
        
    
    os.makedirs( path, exist_ok = True )
    
def safe_copy2( source, dest ):
    
    copy_metadata = True
    
    if HC.PLATFORM_WINDOWS:
        
        mtime = os.path.getmtime( source )
        
        # this is 1980-01-01 UTC, before which Windows can have trouble copying lmaoooooo
        if mtime < 315532800:
            
            copy_metadata = False
            
        
    
    if copy_metadata:
        
        # this overwrites on conflict without hassle
        shutil.copy2( source, dest )
        
    else:
        
        shutil.copy( source, dest )
        
    
def MergeFile( source, dest ):
    
    # this can merge a file, but if it is given a dir it will just straight up overwrite not merge
    
    if os.path.exists( source ) and os.path.exists( dest ) and os.path.samefile( source, dest ):
        
        raise Exception( f'Woah, "{source}" and "{dest}" are the same file!' )
        
    
    if not os.path.isdir( source ):
        
        if PathsHaveSameSizeAndDate( source, dest ):
            
            DeletePath( source )
            
            return True
            
        
    
    try:
        
        # this overwrites on conflict without hassle
        shutil.move( source, dest, copy_function = safe_copy2 )
        
    except Exception as e:
        
        HydrusData.ShowText( 'Trying to move ' + source + ' to ' + dest + ' caused the following problem:' )
        
        HydrusData.ShowException( e )
        
        return False
        
    
    return True
    

def MergeTree( source, dest, text_update_hook = None ):
    
    if os.path.exists( source ) and os.path.exists( dest ) and os.path.samefile( source, dest ):
        
        raise Exception( f'Woah, "{source}" and "{dest}" are the same directory!' )
        
    
    pauser = HydrusData.BigJobPauser()
    
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
        
        num_errors = 0
        
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
                
                if num_errors > 5:
                    
                    raise Exception( 'Too many errors, directory move abandoned.' )
                    
                
                pauser.Pause()
                
                source_path = os.path.join( root, filename )
                dest_path = os.path.join( dest_root, filename )
                
                ok = MergeFile( source_path, dest_path )
                
                if not ok:
                    
                    num_errors += 1
                    
                
            
        
        if num_errors == 0:
            
            DeletePath( source )
            
        
    

def MirrorFile( source, dest ):
    
    if os.path.exists( source ) and os.path.exists( dest ) and os.path.samefile( source, dest ):
        
        return True
        
    
    if not PathsHaveSameSizeAndDate( source, dest ):
        
        try:
            
            TryToMakeFileWriteable( dest )
            
            safe_copy2( source, dest )
            
        except Exception as e:
            
            HydrusData.ShowText( 'Trying to copy ' + source + ' to ' + dest + ' caused the following problem:' )
            
            HydrusData.ShowException( e )
            
            return False
            
        
    
    return True
    
def MirrorTree( source, dest, text_update_hook = None, is_cancelled_hook = None ):
    
    if os.path.exists( source ) and os.path.exists( dest ) and os.path.samefile( source, dest ):
        
        return
        
    
    pauser = HydrusData.BigJobPauser()
    
    MakeSureDirectoryExists( dest )
    
    num_errors = 0
    
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
            
            if num_errors > 5:
                
                raise Exception( 'Too many errors, directory copy abandoned.' )
                
            
            pauser.Pause()
            
            source_path = os.path.join( root, filename )
            
            dest_path = os.path.join( dest_root, filename )
            
            surplus_dest_paths.discard( dest_path )
            
            ok = MirrorFile( source_path, dest_path )
            
            if not ok:
                
                num_errors += 1
                
            
        
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
    
    try:
        
        stat_result = os.stat( path )
        
        current_bits = stat_result.st_mode
        
        if not current_bits & stat.S_IWRITE:
            
            # read-only file, cannot do the rename check
            
            return True
            
        
        os.rename( path, path ) # rename a path to itself
        
        return True
        
    except OSError as e: # 'already in use by another process' or an odd filename too long error
        
        HydrusData.Print( 'Already in use/inaccessible: ' + path )
        
    
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
        
    
    if os.path.exists( path ):
        
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
    
    force_ntfs = GetFileSystemType( directory_path ).lower() in ( 'ntfs', 'exfat' )
    
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
        
    
