import os
import queue
import subprocess
import threading

from hydrus.core import HydrusBoot
from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusData
from hydrus.core import HydrusEnvironment
from hydrus.core import HydrusExceptions
from hydrus.core import HydrusGlobals as HG
from hydrus.core import HydrusNumbers
from hydrus.core import HydrusTime

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
        
        sbp_kwargs[ 'text' ] = True
        sbp_kwargs[ 'encoding' ] = 'utf-8'
        sbp_kwargs[ 'errors' ] = 'replace' # handling mp4s with invalid utf-8 metadata hooray
        
    
    if hide_terminal:
        
        sbp_kwargs[ 'startupinfo' ] = GetSubprocessHideTerminalStartupInfo()
        
    
    if HG.subprocess_report_mode:
        
        message = 'KWargs are: {}'.format( sbp_kwargs )
        
        HydrusData.ShowText( message )
        
    
    return sbp_kwargs
    

long_lived_external_processes_lock = threading.Lock()
long_lived_external_processes = set()

def ReapDeadLongLivedExternalProcesses():
    
    with long_lived_external_processes_lock:
        
        for process in list( long_lived_external_processes ):
            
            return_code = process.poll()
            
            if return_code is not None:
                
                # this process is dead and reaped, all good to lose it now
                long_lived_external_processes.discard( process )
                
            
        
    

def RegisterLongLivedExternalProcess( process: subprocess.Popen ):
    
    with long_lived_external_processes_lock:
        
        long_lived_external_processes.add( process )
        
    

def ReportTimeoutError( cmd, timeout, stdout, stderr ):
    
    if stdout is None:
        
        stdout_text = 'no content'
        
    else:
        
        stdout_text = stdout[:256]
        
    
    if stderr is None:
        
        stderr_text = 'no content'
        
    else:
        
        stderr_text = stderr[:256]
        
    
    message = f'A call to another executable took too long (over {HydrusNumbers.ToHumanInt(timeout)} seconds) to finish! The call was: {cmd}'
    message += '\n\n'
    message += '========== stdout =========='
    message += repr( stdout_text )
    message += '========== stderr =========='
    message += repr( stderr_text )
    message += '============================'
    
    raise HydrusExceptions.SubprocessTimedOut( message )
    

def RunSubprocessRawCall( cmd, start_new_session, bufsize, stdin_pipe, stdout_pipe, stderr_pipe, hide_terminal, text ):
    
    sbp_kwargs = GetSubprocessKWArgs( hide_terminal = hide_terminal, text = text )
    
    try:
        
        return subprocess.Popen( cmd, start_new_session = start_new_session, bufsize = bufsize, stdin = stdin_pipe, stdout = stdout_pipe, stderr = stderr_pipe, **sbp_kwargs )
        
    except FileNotFoundError:
        
        HydrusData.ShowText( f'Got a file not found on this external program call: {cmd}')
        HydrusData.ShowText( f'If the error is not obvious, you might want to talk to hydev about it. Maybe your env PATH is unusual. Your env will follow, and here were the sbp kwargs used in the subprocess call: {sbp_kwargs}')
        HydrusEnvironment.DumpEnv()
        
        raise
        
    except Exception as e:
        
        HydrusData.ShowText( f'Had a problem with an external program! Error will follow; command was: {cmd}' )
        HydrusData.ShowException( e )
        
        raise
        
    

def RunSubprocess( cmd, timeout: int = 15, bufsize: int = 65536, this_is_a_potentially_long_lived_external_guy = False, hide_terminal = True, text = True ):
    
    if this_is_a_potentially_long_lived_external_guy:
        
        # sets non-child in POSIX--it does the os.setsid( None ) nicely
        start_new_session = True
        
        stdin_pipe = None
        stdout_pipe = None
        stderr_pipe = None
        
    else:
        
        start_new_session = False
        
        stdin_pipe = subprocess.PIPE
        stdout_pipe = subprocess.PIPE
        stderr_pipe = subprocess.PIPE
        
    
    process = RunSubprocessRawCall( cmd, start_new_session, bufsize, stdin_pipe, stdout_pipe, stderr_pipe, hide_terminal, text )
    
    if this_is_a_potentially_long_lived_external_guy:
        
        RegisterLongLivedExternalProcess( process )
        
        return ( None, None )
        
    
    ( stdout, stderr ) = SubprocessCommunicate( cmd, process, timeout )
    
    if HG.subprocess_report_mode:
        
        if stdout is None and stderr is None:
            
            HydrusData.ShowText( 'No stdout or stderr came back.' )
            
        
        if stdout is not None:
            
            HydrusData.ShowText( 'stdout: ' + repr( stdout ) )
            
        
        if stderr is not None:
            
            HydrusData.ShowText( 'stderr: ' + repr( stderr ) )
            
        
    
    return ( stdout, stderr )
    

def SubprocessCommunicate( cmd, process: subprocess.Popen, timeout: int ):
    
    def do_shutdown_test():
        
        if HG.model_shutdown:
            
            try:
                
                process.kill()
                
            except Exception as e:
                
                pass
                
            
            raise HydrusExceptions.ShutdownException( 'Application is shutting down!' )
            
        
    
    def do_timeout_test():
        
        if HydrusTime.TimeHasPassedFloat( time_started + timeout ):
            
            ( stdout, stderr ) = TerminateAndReapProcess( process )
            
            ReportTimeoutError( cmd, timeout, stdout, stderr )
            
        
    
    time_started = HydrusTime.GetNowFloat()
    
    do_shutdown_test()
    
    while True:
        
        try:
            
            return process.communicate( timeout = 3 )
            
        except subprocess.TimeoutExpired:
            
            do_timeout_test()
            do_shutdown_test()
            
        
    

def TerminateAndReapProcess( process: subprocess.Popen ):
    
    # you have to do the communicate after the kill calls or otherwise you get zombies
    
    process.terminate()
    
    try:
        
        ( stdout, stderr ) = process.communicate( timeout = 1 )
        
    except subprocess.TimeoutExpired:
        
        process.kill()
        
        ( stdout, stderr ) = process.communicate()
        
    
    return ( stdout, stderr )
    

class SubprocessContext( object ):
    
    def __init__( self, cmd, timeout: int = 15, bufsize: int = 65536, hide_terminal = True, text = True ):
        
        self.finished = False
        
        self._cmd = cmd
        
        self._new_chunk_desired = threading.Event()
        self._chunk_queue = queue.Queue()
        
        self.SENTINEL = None
        
        start_new_session = False
        
        stdin_pipe = subprocess.PIPE
        stdout_pipe = subprocess.PIPE
        stderr_pipe = subprocess.PIPE
        
        self._timeout = timeout
        self._bufsize = bufsize
        
        self.process = RunSubprocessRawCall( cmd, start_new_session, bufsize, stdin_pipe, stdout_pipe, stderr_pipe, hide_terminal, text )
        
        HG.controller.CallToThread( self._THREADReader )
        
    
    def _THREADReader( self ):
        
        try:
            
            while True:
                
                try:
                    
                    HydrusData.CheckProgramIsNotShuttingDown()
                    
                except HydrusExceptions.ShutdownException:
                    
                    return
                    
                
                if self.process.returncode is not None:
                    
                    return
                    
                
                if not self._chunk_queue.empty():
                    
                    self._new_chunk_desired.wait( 1.0 )
                    
                    self._new_chunk_desired.clear()
                    
                    continue
                    
                
                if self.process.returncode is not None:
                    
                    return
                    
                
                try:
                    
                    chunk = self.process.stdout.read( self._bufsize )
                    
                except ValueError: # probably got terminated at an inconvenient time
                    
                    HydrusData.Print( f'Probably not a big deal, but the Subprocess Command "{self._cmd}" closed its stdout early. If this keeps happening, please let hydev know!' )
                    
                    return
                    
                
                if len( chunk ) == 0:
                    
                    return
                    
                
                self._chunk_queue.put( chunk )
                
            
        finally:
            
            self._chunk_queue.put( self.SENTINEL )
            
        
    
    def __enter__( self ):
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self.CloseProcess()
        
    
    def CloseProcess( self ):
        
        self.process.poll()
        
        if self.process.returncode is None:
            
            TerminateAndReapProcess( self.process )
            
        
    

class SubprocessContextReader( SubprocessContext ):
    
    def ReadChunk( self ):
        
        try:
            
            self._new_chunk_desired.set()
            
            chunk = self._chunk_queue.get( timeout = self._timeout )
            
        except queue.Empty:
            
            ( stdout, stderr ) = TerminateAndReapProcess( self.process )
            
            ReportTimeoutError( self._cmd, self._timeout, stdout, stderr )
            
        
        if chunk == self.SENTINEL:
            
            return b''
            
        else:
            
            return chunk
            
        
    

class SubprocessContextStreamer( SubprocessContext ):
    
    def IterateChunks( self ):
        
        while True:
            
            try:
                
                self._new_chunk_desired.set()
                
                chunk = self._chunk_queue.get( timeout = self._timeout )
                
            except queue.Empty:
                
                ( stdout, stderr ) = TerminateAndReapProcess( self.process )
                
                ReportTimeoutError( self._cmd, self._timeout, stdout, stderr )
                
            
            if chunk == self.SENTINEL:
                
                return
                
            else:
                
                yield chunk
                
            
        
    
