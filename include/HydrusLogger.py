import HydrusConstants as HC
import HydrusData
import os
import sys
import threading
import time

class HydrusLogger( object ):
    
    def __init__( self, base_dir, prefix ):
        
        self._log_path_base = os.path.join( base_dir, prefix )
        self._lock = threading.Lock()
        
    
    def __enter__( self ):
        
        self._previous_sys_stdout = sys.stdout
        self._previous_sys_stderr = sys.stderr
        
        self._problem_with_previous_stdout = False
        
        sys.stdout = self
        sys.stderr = self
        
        self._OpenLog()
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self._CloseLog()
        
        sys.stdout = self._previous_sys_stdout
        sys.stderr = self._previous_sys_stderr
        
        return False
        
    
    def _CloseLog( self ):
        
        self._log_file.close()
        
    
    def _GetLogPath( self ):
        
        current_time_struct = time.gmtime()
        
        ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
        
        log_path = self._log_path_base + ' - ' + str( current_year ) + '-' + str( current_month ) + '.log'
        
        return log_path
        
    
    def _OpenLog( self ):
        
        self._log_path = self._GetLogPath()
        
        self._log_file = open( self._log_path, 'a' )
        
    
    def _SwitchToANewLogFileIfDue( self ):
        
        correct_log_path = self._GetLogPath()
        
        if correct_log_path != self._log_path:
            
            self._CloseLog()
            
            self._OpenLog()
            
        
    
    def flush( self ):
        
        with self._lock:
            
            if not self._problem_with_previous_stdout:
                
                try:
                    
                    self._previous_sys_stdout.flush()
                    
                except IOError:
                    
                    self._problem_with_previous_stdout = True
                    
                
            
            self._log_file.flush()
            
            self._SwitchToANewLogFileIfDue()
            
        
    
    def isatty( self ):
        
        return False
        
    
    def write( self, value ):
        
        with self._lock:
            
            if value in ( os.linesep, '\n' ):
                
                prefix = ''
                
            else:
                
                prefix = time.strftime( '%Y/%m/%d %H:%M:%S: ', time.localtime() )
                
            
            message = prefix + value
            
            if not self._problem_with_previous_stdout:
                
                stdout_message = HydrusData.ToByteString( message.replace( u'\u2026', '...' ) )
                
                try:
                    
                    self._previous_sys_stdout.write( stdout_message )
                    
                except IOError:
                    
                    self._problem_with_previous_stdout = True
                    
                
            
            log_message = HydrusData.ToByteString( message )
            
            self._log_file.write( log_message )
            
        
    
