import gc
import HydrusConstants as HC
import HydrusData
import HydrusGlobals
import os
import psutil
import send2trash
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import traceback

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
        
        gc.collect()
        
        try:
            
            os.remove( temp_path )
            
        except OSError:
            
            HydrusData.Print( 'Could not delete the temporary file ' + temp_path )
            
        
    
def ConvertAbsPathToPortablePath( abs_path, base_dir_override = None ):
    
    try:
        
        if base_dir_override is None:
            
            base_dir = HydrusGlobals.controller.GetDBDir()
            
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
            
            base_dir = HydrusGlobals.controller.GetDBDir()
            
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
            
            if 'Error 32' in HydrusData.ToUnicode( e ):
                
                # file in use by another process
                
                HydrusData.DebugPrint( 'Trying to delete ' + path + ' failed because it was in use by another process.' )
                
            else:
                
                HydrusData.ShowText( 'Trying to delete ' + path + ' caused the following error:' )
                HydrusData.ShowException( e )
                
            
        
    
def FilterFreePaths( paths ):
    
    free_paths = []
    
    for path in paths:
        
        try:
            
            os.rename( path, path ) # rename a path to itself
            
            free_paths.append( path )
            
        except OSError as e: # 'already in use by another process'
            
            HydrusData.Print( 'Already in use: ' + path )
            
        
    
    return free_paths
    
def GetDevice( path ):
    
    path = path.lower()
    
    partition_infos = psutil.disk_partitions()
    
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
    
def GetTempFile(): return tempfile.TemporaryFile()
def GetTempFileQuick(): return tempfile.SpooledTemporaryFile( max_size = 1024 * 1024 * 4 )
def GetTempPath( suffix = '' ):
    
    return tempfile.mkstemp( suffix = suffix, prefix = 'hydrus' )
    
def HasSpaceForDBTransaction( db_dir, num_bytes ):
    
    temp_dir = tempfile.gettempdir()
    
    temp_disk_free_space = GetFreeSpace( temp_dir )
    
    a = GetDevice( temp_dir )
    b = GetDevice( db_dir )
    
    if GetDevice( temp_dir ) == GetDevice( db_dir ):
        
        space_needed = int( num_bytes * 2.2 )
        
        if temp_disk_free_space < space_needed:
            
            return ( False, 'I believe you need about ' + HydrusData.ConvertIntToBytes( space_needed ) + ' on your db\'s partition, which I think also holds your temporary path, but you only seem to have ' + HydrusData.ConvertIntToBytes( temp_disk_free_space ) + '.' )
            
        
    else:
        
        space_needed = int( num_bytes * 1.1 )
        
        if temp_disk_free_space < space_needed:
            
            return ( False, 'I believe you need about ' + HydrusData.ConvertIntToBytes( space_needed ) + ' on your temporary path\'s partition, which I think is ' + temp_dir + ', but you only seem to have ' + HydrusData.ConvertIntToBytes( temp_disk_free_space ) + '.' )
            
        
        db_disk_free_space = GetFreeSpace( db_dir )
        
        if db_disk_free_space < space_needed:
            
            return ( False, 'I believe you need about ' + HydrusData.ConvertIntToBytes( space_needed ) + ' on your db\'s partition, but you only seem to have ' + HydrusData.ConvertIntToBytes( db_disk_free_space ) + '.' )
            
        
    
    return ( True, 'You seem to have enough space!' )
    
def LaunchDirectory( path ):
    
    def do_it():
        
        if HC.PLATFORM_WINDOWS:
            
            os.startfile( path )
            
        else:
            
            if HC.PLATFORM_OSX: cmd = [ 'open' ]
            elif HC.PLATFORM_LINUX: cmd = [ 'xdg-open' ]
            
            cmd.append( path )
            
            process = subprocess.Popen( cmd, startupinfo = HydrusData.GetSubprocessStartupInfo() )
            
            process.wait()
            
            process.communicate()
            
        
    
    thread = threading.Thread( target = do_it )
    
    thread.daemon = True
    
    thread.start()
    
def LaunchFile( path ):
    
    def do_it():
        
        if HC.PLATFORM_WINDOWS:
            
            os.startfile( path )
            
        else:
            
            if HC.PLATFORM_OSX: cmd = [ 'open' ]
            elif HC.PLATFORM_LINUX: cmd = [ 'xdg-open' ]
            
            cmd.append( path )
            
            process = subprocess.Popen( cmd, startupinfo = HydrusData.GetSubprocessStartupInfo() )
            
            process.wait()
            
            process.communicate()        
            
        
    
    thread = threading.Thread( target = do_it )
    
    thread.daemon = True
    
    thread.start()
    
def MakeSureDirectoryExists( path ):
    
    if not os.path.exists( path ):
        
        os.makedirs( path )
        
    
def MakeFileWritable( path ):
    
    try:
        
        os.chmod( path, stat.S_IWRITE | stat.S_IREAD )
        
        if os.path.isdir( path ):
            
            for ( root, dirnames, filenames ) in os.walk( path ):
                
                for filename in filenames:
                    
                    sub_path = os.path.join( root, filename )
                    
                    os.chmod( sub_path, stat.S_IWRITE | stat.S_IREAD )
                    
                
            
        
    except Exception as e:
        
        pass
        
    
def MergeFile( source, dest ):
    
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
    
def MergeTree( source, dest ):
    
    pauser = HydrusData.BigJobPauser()
    
    if not os.path.exists( dest ):
        
        shutil.move( source, dest )
        
    else:
        
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
            
            # this overwrites on conflict without hassle
            shutil.copy2( source, dest )
            
        except Exception as e:
            
            HydrusData.ShowText( 'Trying to copy ' + source + ' to ' + dest + ' caused the following problem:' )
            
            HydrusData.ShowException( e )
            
            return False
            
        
    
    return True
    
def MirrorTree( source, dest ):
    
    pauser = HydrusData.BigJobPauser()
    
    MakeSureDirectoryExists( dest )
    
    num_errors = 0
    
    for ( root, dirnames, filenames ) in os.walk( source ):
        
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
            
        
    
def PathsHaveSameSizeAndDate( path1, path2 ):
    
    if os.path.exists( path1 ) and os.path.exists( path2 ):
        
        same_size = os.path.getsize( path1 ) == os.path.getsize( path2 )
        same_modified_time = int( os.path.getmtime( path1 ) ) == int( os.path.getmtime( path2 ) )
        
        if same_size and same_modified_time:
            
            return True
            
        
    
    return False
    
def ReadFileLikeAsBlocks( f ):
    
    next_block = f.read( HC.READ_BLOCK_SIZE )
    
    while next_block != '':
        
        yield next_block
        
        next_block = f.read( HC.READ_BLOCK_SIZE )
        
    
def RecyclePath( path ):
    
    original_path = path
    
    if HC.PLATFORM_LINUX:
        
        # send2trash for Linux tries to do some Python3 str() stuff in prepping non-str paths for recycling
        
        if not isinstance( path, str ):
            
            try:
                
                path = path.encode( sys.getfilesystemencoding() )
                
            except:
                
                HydrusData.Print( 'Trying to prepare ' + path + ' for recycling created this error:' )
                
                HydrusData.DebugPrint( traceback.format_exc() )
                
                return
                
            
        
    
    if os.path.exists( path ):
        
        MakeFileWritable( path )
        
        try:
            
            send2trash.send2trash( path )
            
        except:
            
            HydrusData.Print( 'Trying to recycle ' + path + ' created this error:' )
            
            HydrusData.DebugPrint( traceback.format_exc() )
            
            HydrusData.Print( 'It has been fully deleted instead.' )
            
            DeletePath( original_path )
            
        
    
