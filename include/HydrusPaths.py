import gc
from . import HydrusConstants as HC
from . import HydrusData
from . import HydrusExceptions
from . import HydrusGlobals as HG
from . import HydrusThreading
import os
import psutil
import re
import send2trash
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import traceback

TEMP_PATH_LOCK = threading.Lock()
IN_USE_TEMP_PATHS = set()

def AppendPathUntilNoConflicts( path ):
    
    ( path_absent_ext, ext ) = os.path.splitext( path )
    
    good_path_absent_ext = path_absent_ext
    
    i = 0
    
    while os.path.exists( good_path_absent_ext + ext ):
        
        good_path_absent_ext = path_absent_ext + '_' + str( i )
        
        i += 1
        
    
    return good_path_absent_ext + ext
    
def CleanUpTempPath( os_file_handle, temp_path ):
    
    try:
        
        os.close( os_file_handle )
        
    except OSError:
        
        gc.collect()
        
        try:
            
            os.close( os_file_handle )
            
        except OSError:
            
            HydrusData.Print( 'Could not close the temporary file ' + temp_path )
            
            return
            
        
    
    try:
        
        os.remove( temp_path )
        
    except OSError:
        
        with TEMP_PATH_LOCK:
            
            IN_USE_TEMP_PATHS.add( ( HydrusData.GetNow(), temp_path ) )
            
        
    
def CleanUpOldTempPaths():
    
    with TEMP_PATH_LOCK:
        
        data = list( IN_USE_TEMP_PATHS )
        
        for row in data:
            
            ( time_failed, temp_path ) = row
            
            if HydrusData.TimeHasPassed( time_failed + 60 ):
                
                try:
                    
                    os.remove( temp_path )
                    
                    IN_USE_TEMP_PATHS.discard( row )
                    
                except OSError:
                    
                    if HydrusData.TimeHasPassed( time_failed + 600 ):
                        
                        IN_USE_TEMP_PATHS.discard( row )
                        
                    
                
            
        

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
    
    if os.path.exists( path ):
        
        MakeFileWritable( path )
        
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
                
            
        
    
def DirectoryIsWritable( path ):
    
    if not os.path.exists( path ):
        
        return False
        
    
    try:
        
        t = tempfile.TemporaryFile( dir = path )
        
        t.close()
        
        return True
        
    except:
        
        return False
        
    
def FilterFreePaths( paths ):
    
    free_paths = []
    
    for path in paths:
        
        HydrusThreading.CheckIfThreadShuttingDown()
        
        if PathIsFree( path ):
            
            free_paths.append( path )
            
        
    
    return free_paths
    
def GetCurrentTempDir():
    
    return tempfile.gettempdir()
    
def GetDefaultLaunchPath():
    
    if HC.PLATFORM_WINDOWS:
        
        return 'windows is called directly'
        
    elif HC.PLATFORM_OSX:
        
        return 'open "%path%"'
        
    elif HC.PLATFORM_LINUX:
        
        return 'xdg-open "%path%"'
        
    
def GetDevice( path ):
    
    path = path.lower()
    
    partition_infos = psutil.disk_partitions( all = True )
    
    def sort_descending_mountpoint( partition_info ): # i.e. put '/home' before '/'
        
        return - len( partition_info.mountpoint )
        
    
    partition_infos.sort( key = sort_descending_mountpoint )
    
    for partition_info in partition_infos:
        
        if path.startswith( partition_info.mountpoint.lower() ):
            
            return partition_info.device
            
        
    
    return None
    
def GetFreeSpace( path ):
    
    disk_usage = psutil.disk_usage( path )
    
    return disk_usage.free
    
def GetTempDir( dir = None ):
    
    return tempfile.mkdtemp( prefix = 'hydrus', dir = dir )
    
def SetEnvTempDir( path ):
    
    if not os.path.exists( path ):
        
        raise Exception( 'The given temp directory, "{}", does not exist!'.format( path ) )
        
    
    if not os.path.isdir( path ):
        
        raise Exception( 'The given temp directory, "{}", does not seem to be a directory!'.format( path ) )
        
    
    if not DirectoryIsWritable( path ):
        
        raise Exception( 'The given temp directory, "{}", does not seem to be writable-to!'.format( path ) )
        
    
    for tmp_name in ( 'TMPDIR', 'TEMP', 'TMP' ):
        
        if tmp_name in os.environ:
            
            os.environ[ tmp_name ] = path
            
        
    
    tempfile.tempdir = path
    
def GetTempPath( suffix = '', dir = None ):
    
    return tempfile.mkstemp( suffix = suffix, prefix = 'hydrus', dir = dir )
    
def HasSpaceForDBTransaction( db_dir, num_bytes ):
    
    if HG.no_db_temp_files:
        
        space_needed = int( num_bytes * 1.1 )
        
        approx_available_memory = psutil.virtual_memory().available * 4 / 5
        
        if approx_available_memory < num_bytes:
            
            return ( False, 'I believe you need about ' + HydrusData.ToHumanBytes( space_needed ) + ' available memory, since you are running in no_db_temp_files mode, but you only seem to have ' + HydrusData.ToHumanBytes( approx_available_memory ) + '.' )
            
        
        db_disk_free_space = GetFreeSpace( db_dir )
        
        if db_disk_free_space < space_needed:
            
            return ( False, 'I believe you need about ' + HydrusData.ToHumanBytes( space_needed ) + ' on your db\'s partition, but you only seem to have ' + HydrusData.ToHumanBytes( db_disk_free_space ) + '.' )
            
        
    else:
        
        temp_dir = tempfile.gettempdir()
        
        temp_disk_free_space = GetFreeSpace( temp_dir )
        
        temp_and_db_on_same_device = GetDevice( temp_dir ) == GetDevice( db_dir )
        
        if temp_and_db_on_same_device:
            
            space_needed = int( num_bytes * 2.2 )
            
            if temp_disk_free_space < space_needed:
                
                return ( False, 'I believe you need about ' + HydrusData.ToHumanBytes( space_needed ) + ' on your db\'s partition, which I think also holds your temporary path, but you only seem to have ' + HydrusData.ToHumanBytes( temp_disk_free_space ) + '.' )
                
            
        else:
            
            space_needed = int( num_bytes * 1.1 )
            
            if temp_disk_free_space < space_needed:
                
                return ( False, 'I believe you need about ' + HydrusData.ToHumanBytes( space_needed ) + ' on your temporary path\'s partition, which I think is ' + temp_dir + ', but you only seem to have ' + HydrusData.ToHumanBytes( temp_disk_free_space ) + '.' )
                
            
            db_disk_free_space = GetFreeSpace( db_dir )
            
            if db_disk_free_space < space_needed:
                
                return ( False, 'I believe you need about ' + HydrusData.ToHumanBytes( space_needed ) + ' on your db\'s partition, but you only seem to have ' + HydrusData.ToHumanBytes( db_disk_free_space ) + '.' )
                
            
        
    
    return ( True, 'You seem to have enough space!' )
    
def LaunchDirectory( path ):
    
    def do_it():
        
        if HC.PLATFORM_WINDOWS:
            
            os.startfile( path )
            
        else:
            
            if HC.PLATFORM_OSX:
                
                cmd = [ 'open', path ]
                
            elif HC.PLATFORM_LINUX:
                
                cmd = [ 'xdg-open', path ]
                
            
            # setsid call un-childs this new process
            
            sbp_kwargs = HydrusData.GetSubprocessKWArgs()
            
            process = subprocess.Popen( cmd, preexec_fn = os.setsid, **sbp_kwargs )
            
            process.communicate()
            
        
    
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
                
                # un-childs this new process
                preexec_fn = os.setsid
                
            
            if HG.subprocess_report_mode:
                
                message = 'Attempting to launch ' + path + ' using command ' + repr( cmd ) + '.'
                
                HydrusData.ShowText( message )
                
            
            try:
                
                sbp_kwargs = HydrusData.GetSubprocessKWArgs( hide_terminal = hide_terminal, text = True )
                
                process = subprocess.Popen( cmd, preexec_fn = preexec_fn, stdin = subprocess.PIPE, stdout = subprocess.PIPE, stderr = subprocess.PIPE, **sbp_kwargs )
                
                ( stdout, stderr ) = process.communicate()
                
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
    
    os.makedirs( path, exist_ok = True )
    
def MakeFileWritable( path ):
    
    if not os.path.exists( path ):
        
        return
        
    
    try:
        
        stat_result = os.stat( path )
        
        current_bits = stat_result.st_mode
        
        if HC.PLATFORM_WINDOWS:
            
            # this is actually the same value as S_IWUSR, but let's not try to second guess ourselves
            desired_bits = stat.S_IREAD | stat.S_IWRITE
            
        else:
            
            # guarantee 644 for regular files m8
            desired_bits = stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
            
        
        if not ( desired_bits & current_bits ) == desired_bits:
            
            os.chmod( path, current_bits | desired_bits )
            
        
    except Exception as e:
        
        HydrusData.Print( 'Wanted to add write permission to "{}", but had an error: {}'.format( path, str( e ) ) )
        
    
def MergeFile( source, dest ):
    
    if not os.path.isdir( source ):
        
        MakeFileWritable( source )
        
    
    if PathsHaveSameSizeAndDate( source, dest ):
        
        DeletePath( source )
        
    else:
        
        try:
            
            # this overwrites on conflict without hassle
            shutil.move( source, dest )
            
        except Exception as e:
            
            HydrusData.ShowText( 'Trying to move ' + source + ' to ' + dest + ' caused the following problem:' )
            
            HydrusData.ShowException( e )
            
            return False
            
        
    
    return True
    
def MergeTree( source, dest, text_update_hook = None ):
    
    pauser = HydrusData.BigJobPauser()
    
    if not os.path.exists( dest ):
        
        try:
            
            shutil.move( source, dest )
            
        except OSError:
            
            # if there were read only files in source and this was partition to partition, the copy2 goes ok but the subsequent source unlink fails
            # so, if it seems this has happened, let's just try a walking mergetree, which should be able to deal with these readonlies on a file-by-file basis
            if os.path.exists( dest ):
                
                MergeTree( source, dest, text_update_hook = text_update_hook )
                
            
        
    else:
        
        if len( os.listdir( dest ) ) == 0:
            
            for filename in os.listdir( source ):
                
                source_path = os.path.join( source, filename )
                dest_path = os.path.join( dest, filename )
                
                if not os.path.isdir( source_path ):
                    
                    MakeFileWritable( source_path )
                    
                
                shutil.move( source_path, dest_path )
                
            
        else:
            
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
    
    if not PathsHaveSameSizeAndDate( source, dest ):
        
        try:
            
            MakeFileWritable( dest )
            
            # this overwrites on conflict without hassle
            shutil.copy2( source, dest )
            
        except Exception as e:
            
            HydrusData.ShowText( 'Trying to copy ' + source + ' to ' + dest + ' caused the following problem:' )
            
            HydrusData.ShowException( e )
            
            return False
            
        
    
    return True
    
def MirrorTree( source, dest, text_update_hook = None, is_cancelled_hook = None ):
    
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
            
        elif HC.PLATFORM_OSX:
            
            cmd = [ 'open', '-R', path ]
            
        elif HC.PLATFORM_LINUX:
            
            raise NotImplementedError( 'Linux cannot open file locations!' )
            
        
        sbp_kwargs = HydrusData.GetSubprocessKWArgs( hide_terminal = False )
        
        process = subprocess.Popen( cmd, **sbp_kwargs )
        
        process.communicate()
        
    
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
    
    if os.path.exists( path ):
        
        MakeFileWritable( path )
        
        try:
            
            send2trash.send2trash( path )
            
        except:
            
            HydrusData.Print( 'Trying to recycle ' + path + ' created this error:' )
            
            HydrusData.DebugPrint( traceback.format_exc() )
            
            HydrusData.Print( 'It has been fully deleted instead.' )
            
            DeletePath( path )
            
        
    
def SanitizeFilename( filename ):
    
    if HC.PLATFORM_WINDOWS:
        
        # \, /, :, *, ?, ", <, >, |
        filename = re.sub( r'\\|/|:|\*|\?|"|<|>|\|', '_', filename )
        
    else:
        
        filename = re.sub( '/', '_', filename )
        
    
    return filename
    
