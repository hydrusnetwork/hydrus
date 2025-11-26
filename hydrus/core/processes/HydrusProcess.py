import os
import sys
import time

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusExceptions
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
    
