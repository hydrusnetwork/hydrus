from . import HydrusConstants as HC
from . import HydrusData
import os
import sys
import threading
import time

class HydrusLogger( object ):
    
    def __init__( self, db_dir, prefix ):
        
        self._db_dir = db_dir
        self._prefix = prefix
        
        self._log_path_base = self._GetLogPathBase()
        self._lock = threading.Lock()
        
        self._log_closed = False
        
    
    def __enter__( self ):
        
        self._previous_sys_stdout = sys.stdout
        self._previous_sys_stderr = sys.stderr
        
        self._problem_with_previous_stdout = False
        
        self._OpenLog()
        
        sys.stdout = self
        sys.stderr = self
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        #sys.stdout = self._previous_sys_stdout
        #sys.stderr = self._previous_sys_stderr
        
        self._CloseLog()
        
        self._log_closed = True
        
        return False
        
    
    def _CloseLog( self ):
        
        self._log_file.close()
        
    
    def _GetLogPath( self ):
        
        current_time_struct = time.localtime()
        
        ( current_year, current_month ) = ( current_time_struct.tm_year, current_time_struct.tm_mon )
        
        log_path = self._log_path_base + ' - ' + str( current_year ) + '-' + str( current_month ) + '.log'
        
        return log_path
        
    
    def _GetLogPathBase( self ):
        
        return os.path.join( self._db_dir, self._prefix )
        
    
    def _OpenLog( self ):
        
        self._log_path = self._GetLogPath()
        
        is_new_file = not os.path.exists( self._log_path )
        
        self._log_file = open( self._log_path, 'a', encoding = 'utf-8' )
        
        if is_new_file:
            
            self._log_file.write( u'\uFEFF' ) # Byte Order Mark, BOM, to help reader software interpret this as utf-8
            
        
    
    def _SwitchToANewLogFileIfDue( self ):
        
        correct_log_path = self._GetLogPath()
        
        if correct_log_path != self._log_path:
            
            self._CloseLog()
            
            self._OpenLog()
            
        
    
    def flush( self ):
        
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
            
        
    
    def isatty( self ):
        
        return False
        
    
    def write( self, value ):
        
        if self._log_closed:
            
            return
            
        
        with self._lock:
            
            if value in ( os.linesep, '\n' ):
                
                prefix = ''
                
            else:
                
                prefix = time.strftime( '%Y/%m/%d %H:%M:%S: ' )
                
            
            message = prefix + value
            
            if not self._problem_with_previous_stdout:
                
                try:
                    
                    self._previous_sys_stdout.write( message )
                    
                except:
                    
                    self._problem_with_previous_stdout = True
                    
                
            
            self._log_file.write( message )
            
        
    
