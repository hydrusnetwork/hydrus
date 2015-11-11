import HydrusConstants as HC
import os
import sys
import time

class HydrusLogger( object ):
    
    def __init__( self, log_filename ):
        
        self._log_filename = log_filename
        
    
    def __enter__( self ):
        
        self._previous_sys_stdout = sys.stdout
        self._previous_sys_stderr = sys.stderr
        
        sys.stdout = self
        sys.stderr = self
        
        self._log_file = open( os.path.join( HC.LOGS_DIR, self._log_filename ), 'a' )
        
        return self
        
    
    def __exit__( self, exc_type, exc_val, exc_tb ):
        
        self._log_file.close()
        
        sys.stdout = self._previous_sys_stdout
        sys.stderr = self._previous_sys_stderr
        
        return False
        
    
    def flush( self ):
        
        self._previous_sys_stdout.flush()
        self._log_file.flush()
        
    
    def write( self, value ):
        
        if value in ( os.linesep, '\n' ):
            
            prefix = ''
            
        else:
            
            prefix = time.strftime( '%Y/%m/%d %H:%M:%S: ', time.localtime() )
            
        
        message = prefix + value
        
        self._previous_sys_stdout.write( message )
        self._log_file.write( message )
        
    