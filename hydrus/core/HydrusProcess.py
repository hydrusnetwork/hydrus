import os
import subprocess
import sys
import time

from hydrus.core import HydrusBoot
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusEnvironment
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusPSUtil
from hydrus.core import HydrusText

def GetSiblingProcessPorts( db_path, instance ):
    
    path = os.path.join( db_path, instance + '_running' )
    
    if os.path.exists( path ):
        
        with open( path, 'r', encoding = 'utf-8' ) as f:
            
            file_text = f.read()
            
            try:
                
                ( pid, create_time ) = HydrusText.DeserialiseNewlinedTexts( file_text )
                
                pid = int( pid )
                
            except ValueError:
                
                return None
                
            
            if not HydrusPSUtil.PSUTIL_OK:
                
                raise HydrusExceptions.CancelledException( 'psutil is not available--cannot determine sibling process ports!' )
                
            
            try:
                
                if HydrusPSUtil.psutil.pid_exists( pid ):
                    
                    ports = []
                    
                    p = HydrusPSUtil.psutil.Process( pid )
                    
                    for conn in p.net_connections():
                        
                        if conn.status == 'LISTEN':
                            
                            ports.append( int( conn.laddr[1] ) )
                            
                        
                    
                    return ports
                    
                
            except HydrusPSUtil.psutil.Error:
                
                return None
                
            
        
    
    return None
    

def GetSubprocessEnv():
    
    if HG.subprocess_report_mode:
        
        HydrusEnvironment.DumpEnv()
        
    
    env = os.environ.copy()
    
    if HydrusBoot.ORIGINAL_PATH is not None:
        
        env[ 'PATH' ] = HydrusBoot.ORIGINAL_PATH
        
    
    if HC.RUNNING_FROM_FROZEN_BUILD:
        
        # let's make a proper env for subprocess that doesn't have pyinstaller woo woo in it
        
        changes_made = False
        
        orig_swaperoo_strings = [ 'LD_LIBRARY_PATH', 'XDG_DATA_DIRS'  ]
        ok_to_remove_absent_orig = [ 'LD_LIBRARY_PATH' ]
        
        for key in orig_swaperoo_strings:
            
            orig_key = '{}_ORIG'.format( key )
            
            if orig_key in env:
                
                env[ key ] = env[ orig_key ]
                
                changes_made = True
                
            elif key in env and key in ok_to_remove_absent_orig:
                
                del env[ key ]
                
                changes_made = True
                
            
        
        remove_if_hydrus_base_dir = [ 'QT_PLUGIN_PATH', 'QML2_IMPORT_PATH', 'SSL_CERT_FILE' ]
        hydrus_base_dir = HG.controller.GetDBDir()
        
        for key in remove_if_hydrus_base_dir:
            
            if key in env and env[ key ].startswith( hydrus_base_dir ):
                
                del env[ key ]
                
                changes_made = True
                
            
        
        if ( HC.PLATFORM_LINUX or HC.PLATFORM_MACOS ):
            
            if 'PATH' in env:
                
                # fix for pyinstaller, which drops this stuff for some reason and hence breaks ffmpeg
                
                path = env[ 'PATH' ]
                
                path_locations = set( path.split( ':' ) )
                desired_path_locations = [ '/usr/bin', '/usr/local/bin' ]
                
                for desired_path_location in desired_path_locations:
                    
                    if desired_path_location not in path_locations:
                        
                        path = desired_path_location + ':' + path
                        
                        env[ 'PATH' ] = path
                        
                        changes_made = True
                        
                    
                
            
            if 'XDG_DATA_DIRS' in env:
                
                xdg_data_dirs = env[ 'XDG_DATA_DIRS' ]
                
                # pyinstaller can just replace this nice usually long str with multiple paths with base_dir/share
                # absent the _orig above to rescue this, we'll populate with basic
                if ':' not in xdg_data_dirs and HC.BASE_DIR in xdg_data_dirs:
                    
                    xdg_data_dirs = '/usr/local/share:/usr/share'
                    
                    changes_made = True
                    
                
            
        
        if not changes_made:
            
            env = None
            
        
    else:
        
        env = None
        
    
    return env
    

def GetSubprocessHideTerminalStartupInfo():
    
    if HC.PLATFORM_WINDOWS:
        
        # This suppresses the terminal window that tends to pop up when calling ffmpeg or whatever
        
        startupinfo = subprocess.STARTUPINFO()
        
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        
    else:
        
        startupinfo = None
        
    
    return startupinfo
    

def GetSubprocessKWArgs( hide_terminal = True, text = False ):
    
    sbp_kwargs = {}
    
    sbp_kwargs[ 'env' ] = GetSubprocessEnv()
    
    if text:
        
        # probably need to override the stdXXX pipes with i/o encoding wrappers in the case of 3.5 here
        
        if sys.version_info.minor >= 6:
            
            sbp_kwargs[ 'encoding' ] = 'utf-8'
            
        
        if sys.version_info.minor >= 7:
            
            sbp_kwargs[ 'text' ] = True
            
        else:
            
            sbp_kwargs[ 'universal_newlines' ] = True
            
        
    
    if hide_terminal:
        
        sbp_kwargs[ 'startupinfo' ] = GetSubprocessHideTerminalStartupInfo()
        
    
    if HG.subprocess_report_mode:
        
        message = 'KWargs are: {}'.format( sbp_kwargs )
        
        HydrusData.ShowText( message )
        
    
    return sbp_kwargs
    

def IsAlreadyRunning( db_path, instance ):
    
    if not HydrusPSUtil.PSUTIL_OK:
        
        HydrusData.Print( 'psutil is not available, so cannot do the "already running?" check!' )
        
        return False
        
    
    path = os.path.join( db_path, instance + '_running' )
    
    if os.path.exists( path ):
        
        try:
            
            with open( path, 'r', encoding = 'utf-8' ) as f:
                
                file_text = f.read()
                
                try:
                    
                    ( pid, create_time ) = HydrusText.DeserialiseNewlinedTexts( file_text )
                    
                    pid = int( pid )
                    create_time = float( create_time )
                    
                except ValueError:
                    
                    return False
                    
                
                def time_matches( process_time: float, recorded_time: float ):
                    
                    # since some timestamps here can be just slightly off due to float gubbins, let's allow a broader test so other processes can force a lock by making their own 'I want the lock' running file
                    
                    return recorded_time - 0.5 < process_time < recorded_time + 0.5
                    
                
                try:
                    
                    me = HydrusPSUtil.psutil.Process()
                    
                    if me.pid == pid and time_matches( me.create_time(), create_time ):
                        
                        # this is me! there is no conflict, lol!
                        # this happens when a linux process restarts with os.execl(), for instance (unlike Windows, it keeps its pid)
                        
                        return False
                        
                    
                    if HydrusPSUtil.psutil.pid_exists( pid ):
                        
                        p = HydrusPSUtil.psutil.Process( pid )
                        
                        if time_matches( p.create_time(), create_time ) and p.is_running():
                            
                            return True
                            
                        
                    
                except HydrusPSUtil.psutil.Error:
                    
                    return False
                    
                
            
        except UnicodeDecodeError:
            
            HydrusData.Print( 'The already-running file was incomprehensible!' )
            
            return False
            
        except Exception as e:
            
            HydrusData.Print( 'Problem loading the already-running file:' )
            HydrusData.PrintException( e )
            
            return False
            
        
    
    return False
    

def RecordRunningStart( db_path, instance ):
    
    if not HydrusPSUtil.PSUTIL_OK:
        
        return
        
    
    path = os.path.join( db_path, instance + '_running' )
    
    record_string = ''
    
    try:
        
        me = HydrusPSUtil.psutil.Process()
        
        record_string += str( me.pid )
        record_string += '\n'
        record_string += str( me.create_time() )
        
    except HydrusPSUtil.psutil.Error:
        
        return
        
    
    with open( path, 'w', encoding = 'utf-8' ) as f:
        
        f.write( record_string )
        
    

def RestartProcess():
    
    time.sleep( 1 ) # time for ports to unmap
    
    # note argv is unreliable in weird script-launching situations, but there we go
    exe = sys.executable
    me = sys.argv[0]
    
    if HC.RUNNING_FROM_SOURCE:
        
        # exe is python's exe, me is the script
        
        args = [ exe ] + sys.argv
        
    else:
        
        # we are running a frozen release--both exe and me are the built exe
        
        # wrap it in quotes because pyinstaller passes it on as raw text, breaking any path with spaces :/
        if not me.startswith( '"' ):
            
            me = '"{}"'.format( me )
            
        
        args = [ me ] + sys.argv[1:]
        
    
    os.execv( exe, args )
    
