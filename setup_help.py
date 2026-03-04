#!/usr/bin/env python3
"""
Hydrus help docs builder.
"""

import argparse
import os
import sys
import subprocess

from pathlib import Path

def print_banner():
    
    banner = '''   r::::::::::::::::::::::::::::::::::r
   :                                  :
   :               :PP.               :
   :               vBBr               :
   :               7BB:               :
   :               rBB:               :
   :      :DQRE:   rBB:   :gMBb:      :
   :       :BBBi   rBB:   7BBB.       :
   :        KBB:   rBB:   rBBI        :
   :        qBB:   rBB:   rQBU        :
   :        qBB:   rBB:   iBBS        :
   :        qBB:   iBB:   7BBj        :
   :        iBBY   iBB.   2BB.        :
   :         SBQq  iBQ:  EBBY         :
   :          :MQBZMBBDRBBP.          :
   :              .YBB7               :
   :               :BB.               :
   :               7BBi               :
   :               rBB:               :
   :                                  :
   r::::::::::::::::::::::::::::::::::r

                  hydrus
'''
    
    print(banner)
    

def get_python_exe_path( venv_path ):
    
    if sys.platform == 'win32':
        
        python_exe = venv_path / 'Scripts' / 'python.exe'
        
    else:
        
        python_exe = venv_path / 'bin' / 'python'
        
    
    return python_exe
    

def run_pip( cmd, venv_path ):
    
    python_exe = get_python_exe_path( venv_path )
    
    subprocess.check_call( [ str( python_exe ), '-m', 'pip' ] + cmd )
    

def build_help( venv_path ):
    
    print( 'Checking mkdocs-material...' )
    
    run_pip([ 'install', 'mkdocs-material==9.7.1' ], venv_path )
    
    print( 'Building help...' )
    
    python_exe = get_python_exe_path( venv_path )
    
    subprocess.check_call( [ python_exe, '-m', 'mkdocs', 'build', '-d', 'help' ] )
    

def main():
    
    try:
        
        repo_root = Path( __file__ ).parent
        
        os.chdir( repo_root )
        
        argparser = argparse.ArgumentParser( description = 'hydrus network help setup' )
        
        argparser.add_argument( '-v', '--venv_name', help = 'set the name of the venv folder (default=venv)' )
        
        result = argparser.parse_args()
        
        if result.venv_name is None:
            
            venv_name = 'venv'
            
        else:
            
            venv_name = result.venv_name
            
        
        venv_path = repo_root / venv_name
        
        # Install dependencies
        try:
            
            build_help( venv_path )
            
        except subprocess.CalledProcessError as e:
            
            print( f'ERROR: Build failed: {e}' )
            
            sys.exit(1)
            
        
        print( '--------' )
        print( 'Done!' )
        print()
        
    finally:
        
        if sys.platform == 'win32':
            
            # most Win users are double-clicking the file and would appreciate a moment to see the "Done!" conclusion before the window disappears
            input( 'Hit enter to close...' )
            
        
    

if __name__ == "__main__":
    
    main()
    
