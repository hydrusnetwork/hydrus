import gc
import HydrusConstants as HC
import HydrusData
import os
import psutil
import send2trash
import shutil
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
            
        
    
def ConvertAbsPathToPortablePath( abs_path ):
    
    try: return os.path.relpath( abs_path, HC.BASE_DIR )
    except: return abs_path
    
def ConvertPortablePathToAbsPath( portable_path ):
    
    if os.path.isabs( portable_path ): abs_path = portable_path
    else: abs_path = os.path.normpath( os.path.join( HC.BASE_DIR, portable_path ) )
    
    return abs_path
    
def CopyAndMergeTree( source, dest ):
    
    pauser = HydrusData.BigJobPauser()
    
    if not os.path.exists( dest ):
        
        os.makedirs( dest )
        
    
    for ( root, dirnames, filenames ) in os.walk( source ):
        
        dest_root = root.replace( source, dest )
        
        for dirname in dirnames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, dirname )
            dest_path = os.path.join( dest_root, dirname )
            
            if not os.path.exists( dest_path ):
                
                os.makedirs( dest_path )
                
            
            shutil.copystat( source_path, dest_path )
            
        
        for filename in filenames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, filename )
            dest_path = os.path.join( dest_root, filename )
            
            shutil.copy2( source_path, dest_path )
            
        
    
def CopyFileLikeToFileLike( f_source, f_dest ):
    
    for block in ReadFileLikeAsBlocks( f_source ): f_dest.write( block )
    
def DeletePath( path ):
    
    if os.path.exists( path ):
        
        if os.path.isdir( path ):
            
            shutil.rmtree( path )
            
        else:
            
            os.remove( path )
            
        

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
    
def GetTempFile(): return tempfile.TemporaryFile()
def GetTempFileQuick(): return tempfile.SpooledTemporaryFile( max_size = 1024 * 1024 * 4 )
def GetTempPath(): return tempfile.mkstemp( prefix = 'hydrus' )

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
    
def MirrorTree( source, dest ):
    
    pauser = HydrusData.BigJobPauser()
    
    if not os.path.exists( dest ):
        
        os.makedirs( dest )
        
    
    for ( root, dirnames, filenames ) in os.walk( source ):
        
        dest_root = root.replace( source, dest )
        
        surplus_dest_paths = { os.path.join( dest_root, dest_filename ) for dest_filename in os.listdir( dest_root ) }
        
        for dirname in dirnames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, dirname )
            dest_path = os.path.join( dest_root, dirname )
            
            surplus_dest_paths.discard( dest_path )
            
            if not os.path.exists( dest_path ):
                
                os.makedirs( dest_path )
                
            
            shutil.copystat( source_path, dest_path )
            
        
        for filename in filenames:
            
            pauser.Pause()
            
            source_path = os.path.join( root, filename )
            
            dest_path = os.path.join( dest_root, filename )
            
            surplus_dest_paths.discard( dest_path )
            
            if not PathsHaveSameSizeAndDate( source_path, dest_path ):
                
                shutil.copy2( source_path, dest_path )
                
            
        
        for dest_path in surplus_dest_paths:
            
            pauser.Pause()
            
            DeletePath( dest_path )
            
        
    
def PathsHaveSameSizeAndDate( path1, path2 ):
    
    if os.path.exists( path1 ) and os.path.exists( path2 ):
        
        same_size = os.path.getsize( path1 ) == os.path.getsize( path2 )
        same_modified_time = os.path.getmtime( path1 ) == os.path.getmtime( path2 )
        
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
                
                HydrusData.Print( 'Trying to prepare a file for recycling created this error:' )
                traceback.print_exc()
                
                return
                
            
        
    
    if os.path.exists( path ):
        
        try:
            
            send2trash.send2trash( path )
            
        except:
            
            HydrusData.Print( 'Trying to recycle a file created this error:' )
            traceback.print_exc()
            
            HydrusData.Print( 'It has been fully deleted instead.' )
            
            DeletePath( original_path )
            
        
    