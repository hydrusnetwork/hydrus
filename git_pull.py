#!/usr/bin/env python3
"""
Hydrus git pull convenience script.
"""

import os
import sys
import subprocess

from pathlib import Path

def main():
    
    try:
        
        repo_root = Path( __file__ ).parent
        
        os.chdir( repo_root )
        
        try:
            
            subprocess.check_call( [ 'git', 'pull' ] )
            
        except subprocess.CalledProcessError as e:
            
            print( f'ERROR: Pull failed: {e}' )
            
            sys.exit( 1 )
            
        
        print( '--------' )
        print( 'Done!' )
        print()
        
    finally:
        
        if sys.platform == 'win32':
            
            # most Win users are double-clicking the file and would appreciate a moment to see the "Done!" conclusion before the window disappears
            input( 'Hit enter to close...' )
            
        
    

if __name__ == "__main__":
    
    main()
    
