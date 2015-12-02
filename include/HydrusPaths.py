import gc
import HydrusConstants as HC
import HydrusData
import os
import send2trash
import shutil
import subprocess
import sys
import tempfile
import threading
import traceback

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
    
    if not os.path.exists( dest ):
        
        os.mkdir( dest )
        
    
    for ( root, dirnames, filenames ) in os.walk( source ):
        
        dest_root = root.replace( source, dest )
        
        for dirname in dirnames:
            
            source_path = os.path.join( root, dirname )
            dest_path = os.path.join( dest_root, dirname )
            
            if not os.path.exists( dest_path ):
                
                os.mkdir( dest_path )
                
            
            shutil.copystat( source_path, dest_path )
            
        
        for filename in filenames:
            
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
            
        
    