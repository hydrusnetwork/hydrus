import os
import sys
import threading
import time

from hydrus.core import HydrusConstants as HC

# this guy catches crashes and dumps all thread stacks to original stderr or the stable file handle you pass to it
# I am informed it has zero overhead but it will pre-empt or otherwise mess around with other dump creators
import faulthandler

DO_FAULTHANDLER_STUFF = False

def turn_off_faulthandler():
    
    global DO_FAULTHANDLER_STUFF
    
    DO_FAULTHANDLER_STUFF = False
    
    faulthandler.disable()
    

class HydrusLogger( object ):
    
    def __init__( self, db_dir, prefix ):
        
        self._db_dir = db_dir
        self._prefix = prefix
        
        self._lock = threading.Lock()
        
        self._log_closed = False
        
        self._problem_with_previous_stdout = False
        
        self._previous_sys_stdout = None
        self._previous_sys_stderr = None
        
    
    def __enter__( self ):
        
        self._previous_sys_stdout = sys.stdout
        self._previous_sys_stderr = sys.stderr
        
        self._problem_with_previous_stdout = False
        
        self._OpenLog()
        
        sys.stdout = self
        sys.stderr = self
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self._CloseLog()
        
        sys.stdout = self._previous_sys_stdout
        sys.stderr = self._previous_sys_stderr
        
        self._previous_sys_stdout = None
        self._previous_sys_stderr = None
        
        self._log_closed = True
        
        return False
        
    
    def _CloseLog( self ) -> None:
        
        if DO_FAULTHANDLER_STUFF:
            
            faulthandler.disable()
            
        
        self._log_file.close()
        
    
    def _GetLogPath( self ) -> str:
        
        current_time_struct = time.localtime()
        
        ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
        
        log_filename = '{} - {}-{:02}.log'.format( self._prefix, current_year, current_month )
        
        log_path = os.path.join( self._db_dir, log_filename )
        
        return log_path
        
    
    def _OpenLog( self ) -> None:
        
        self._log_path = self._GetLogPath()
        
        is_new_file = not os.path.exists( self._log_path )
        
        self._log_file = open( self._log_path, 'a', encoding = 'utf-8' )
        
        if DO_FAULTHANDLER_STUFF:
            
            faulthandler.enable( file = self._log_file, all_threads = True )
            
        
        if is_new_file:
            
            self._log_file.write( HC.UNICODE_BYTE_ORDER_MARK ) # Byte Order Mark, BOM, to help reader software interpret this as utf-8
            
        
    
    def _SwitchToANewLogFileIfDue( self ) -> None:
        
        correct_log_path = self._GetLogPath()
        
        if correct_log_path != self._log_path:
            
            self._CloseLog()
            
            self._OpenLog()
            
        
    
    def flush( self ) -> None:
        
        if self._log_closed:
            
            return
            
        
        with self._lock:
            
            if not self._problem_with_previous_stdout:
                
                try:
                    
                    self._previous_sys_stdout.flush()
                    
                except IOError:
                    
                    self._problem_with_previous_stdout = True
                    
                
            
            self._log_file.flush()
            
            self._SwitchToANewLogFileIfDue()
            
        
    
    def isatty( self ) -> bool:
        
        return False
        
    
    def write( self, value ) -> None:
        
        if self._log_closed:
            
            return
            
        
        with self._lock:
            
            if value in ( '\n', '\n' ):
                
                prefix = ''
                
            else:
                
                prefix = 'v{}, {}: '.format( HC.SOFTWARE_VERSION, time.strftime( '%Y-%m-%d %H:%M:%S' ) )
                
            
            message = prefix + value
            
            if not self._problem_with_previous_stdout:
                
                try:
                    
                    self._previous_sys_stdout.write( message )
                    
                except:
                    
                    self._problem_with_previous_stdout = True
                    
                
            
            self._log_file.write( message )
            
        
    
