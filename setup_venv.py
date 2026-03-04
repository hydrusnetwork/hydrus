#!/usr/bin/env python3
"""
Hydrus virtual environment setup script.
Handles interactive configuration and installation of dependencies.
"""

import argparse
import os
import sys
import subprocess
import shutil

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
    

def check_python_version():
    
    print( '--------' )
    print( 'Your Python version is:' )
    print( f'Python {sys.version}' )
    print()
    
    if sys.version_info < ( 3, 10 ):
        
        print( 'WARNING: Python 3.10+ is required!' )
        
        sys.exit( 1 )
        
    elif sys.version_info >= ( 3, 15 ):
        
        print( 'You have a version of python newer than hydev tests with. You will definitely need the advanced install; I do not know if it can work!' )
        
    elif sys.version_info >= ( 3, 14 ):
        
        print( 'You will need the advanced install. Also, select "t" for the (t)est versions of things.' )
        
    

def confirm_venv_delete(venv_path):
    
    if venv_path.exists():
        
        print( 'Virtual environment will be reinstalled. Press Enter to continue.' )
        input()
        print( 'Deleting old venv...' )
        
        shutil.rmtree( venv_path )
        
        if venv_path.exists():
            
            print( 'ERROR: venv directory did not delete. Is it activated elsewhere, like an IDE?' )
            
            sys.exit(1)
            
        
    else:
        
        print( 'If you do not know what this is, check the "running from source" help.' )
        print( 'Press Enter to continue.' )
        input()
        
    

def get_install_type():
    
    print()
    print( 'Do you want the (s)imple or (a)dvanced install?' )
    
    while True:
        
        install_type = input().strip().lower()
        
        if install_type in ( 's', 'a' ):
            
            return install_type
            
        
        print( 'Sorry, did not understand that input! Enter "s" or "a".' )
        
    

def get_user_choice( prompt_text, valid_choices, default_choice: str ):
    
    while True:
        
        prompt = f'{prompt_text} [{default_choice}]: '
        user_input = input(prompt).strip().lower()
        
        if not user_input:
            
            return default_choice
            
        
        if user_input in valid_choices:
            
            return user_input
            
        
        print( 'Sorry, did not understand that input!' )
        
        sys.exit( 1 )
        
    

def process_advanced_options( requirements_dict: dict[ str, str | None ] ):
    """Get advanced requirements customisation from user."""
    
    print( '--------' )
    print( 'We will now choose versions for larger libraries.' )
    print( 'If something does not install, run this script again and it will clear everything and try again.' )
    print( 'Press Enter to use the default choice (shown in brackets).' )
    print()
    
    # Qt
    print( 'Qt (PySide6) - User Interface' )
    print( 'Most people want (n)ormal.' )
    print( 'Very old OSes should try (o)ld. Python 3.14+ should try (t)est.' )
    print( 'If normal Qt does not work, try (o)ld, (q) for PyQt6, or (w)rite your own.' )
    
    qt = get_user_choice( 'Qt choice (o/n/t/q/w)', ( 'o', 'n', 't', 'q', 'w' ), 'n' )
    
    if qt == 'o':
        
        requirements_dict[ 'pyside6' ] = '==6.3.1'
        requirements_dict[ 'qtpy' ] = '==2.3.1'
        
    elif qt == 't':
        
        requirements_dict[ 'pyside6' ] = '==6.10.1'
        requirements_dict[ 'qtpy' ] = '==2.4.3'
        
    elif qt == 'q':
        
        del requirements_dict[ 'pyside6' ]
        
        requirements_dict[ 'pyqt6' ] = None
        requirements_dict[ 'pyqt6-charts' ] = None
        requirements_dict[ 'qtpy' ] = None
        
    elif qt == "w":
        
        print()
        print( 'Enter the exact PySide6 version, e.g. "6.6.0":' )
        print( '- Python 3.10: earliest 6.2.0' )
        print( '- Python 3.11: earliest 6.4.0.1' )
        print( '- Python 3.12: earliest 6.6.0' )
        print( '- Python 3.13: earliest 6.8.0.2' )
        print( '- Python 3.14: earliest 6.10.1' )
        
        qt_custom_pyside6 = input( 'PySide6 version: ' ).strip()
        qt_custom_qtpy = input( 'qtpy version (probably "2.4.3"): ' ).strip()
        
        requirements_dict[ 'pyside6' ] = '==' + qt_custom_pyside6
        requirements_dict[ 'qtpy' ] = '==' + qt_custom_qtpy
        
    
    # no mpv version in testing atm
    '''
    # mpv
    print()
    print( 'mpv - audio and video playback' )
    print( 'Most people want (n)ormal.' )
    
    if sys.platform == "darwin":
        
        print( 'WARNING: mpv is broken on macOS. Choose 'n' as a safe default.' )
        
    
    mpv = get_user_choice( 'mpv choice (n/t)', ( 'n', 't' ), 'n' )
    
    if mpv == 't':
        
        requirements_dict[ 'mpv' ] = '==1.0.8'
        
    '''
    
    # OpenCV
    print()
    print( 'OpenCV - Images' )
    print( 'Most people want (n)ormal.' )
    print( 'Very old OSes should try (o)ld. Python 3.14+ should try (t)est.' )
    opencv = get_user_choice( 'OpenCV choice (o/n/t)', ( 'o', 'n', 't' ), 'n' )
    
    if opencv == 'o':
        
        requirements_dict[ 'opencv-python-headless' ] = '==4.8.1.78'
        requirements_dict[ 'numpy' ] = '<=2.3.1'
        
    elif opencv == 't':
        
        requirements_dict[ 'opencv-python-headless' ] = '==4.13.0.90'
        requirements_dict[ 'numpy' ] = '==2.4.1'
        
    
    # Future libraries
    print()
    print( 'Future Libraries' )
    print( 'There is a test for a new domain parsing library. Want to try it?' )
    future = get_user_choice( 'Future libraries (y/n)', ( 'y', 'n' ), 'n' )
    
    if future == 'y':
        
        requirements_dict[ 'tldextract' ] = '==5.3.1'
        
    
    # Dev mode
    print()
    print( 'Development Tools' )
    print( 'Do you want to install development tools (Httmock, etc.)?' )
    dev = get_user_choice( 'Install dev tools (y/n)', ( 'y', 'n' ), 'n' )
    
    if dev == 'y':
        
        requirements_dict[ 'httmock' ] = '>=1.4.0'
        requirements_dict[ 'mkdocs-material' ] = '==9.7.1'
        
    

def create_venv(venv_path):
    
    print( '--------' )
    print( 'Creating new venv...' )
    
    subprocess.check_call( [ sys.executable, '-m', 'venv', str( venv_path ) ] )
    

def run_pip( cmd, venv_path ):
    """Run pip command in the venv."""
    
    if sys.platform == 'win32':
        
        python_exe = venv_path / 'Scripts' / 'python.exe'
        
    else:
        
        python_exe = venv_path / 'bin' / 'python'
        
    
    subprocess.check_call( [ str( python_exe ), '-m', 'pip' ] + cmd )
    

def install_dependencies( venv_path, requirements_dict: dict[ str, str | None ] ):
    """Install advanced (customized) dependencies."""
    
    print( 'Upgrading pip and wheel...' )
    
    run_pip([ 'install', '--upgrade', 'pip' ], venv_path )
    run_pip([ 'install', '--upgrade', 'wheel' ], venv_path )
    
    print( 'Installing...' )
    
    all_library_parts = [ name if version is None else name + version for ( name, version ) in requirements_dict.items() ]
    
    run_pip( [ 'install' ] + all_library_parts, venv_path )
    

def main():
    
    try:
        
        repo_root = Path( __file__ ).parent
        
        os.chdir( repo_root )
        
        argparser = argparse.ArgumentParser( description = 'hydrus network venv setup' )
        
        argparser.add_argument( '-v', '--venv_name', help = 'set the name of the venv folder (default=venv)' )
        
        result = argparser.parse_args()
        
        if result.venv_name is None:
            
            venv_name = 'venv'
            
        else:
            
            venv_name = result.venv_name
            
        
        print_banner()
        
        check_python_version()
        
        venv_path = repo_root / venv_name
        
        print( f'venv path: {venv_path}' )
        print()
        
        confirm_venv_delete(venv_path)
        
        # OK, hydev is reworking this whole thing to be hacky and outside of the pyproject.toml
        # background: we moved old multi-requirements.txt mess to a shared pyproject.toml that had 'groups' to simulate the old/normal/test choices we take here
        # 'groups' was an imperfect fit, and pyproject.toml is an imperfect place for test libraries
        # to restore a simple pyproject.toml that works as most users will expect, the various weird hydev stuff is thus migrated to this hardcoded list
        # we are basically just being a requirements.txt in code; I care not
        
        requirements_dict = {
            'beautifulsoup4' : '>=4.0.0',
            'cbor2' : '>=5.6.5',
            'chardet' : '>=3.0.4',
            'cryptography' : '>=44.0.0',
            'dateparser' : '==1.2.1',
            'html5lib' : '>=1.0.1',
            'lxml' : '>=4.5.0',
            'lz4' : '>=3.0.0',
            'olefile' : '>=0.47',
            'pillow' : '>=10.0.1',
            'pillow-heif' : '>=0.12.0',
            'pillow-jxl-plugin' : '>=1.3.0',
            'psutil' : '>=5.0.0',
            'pympler' : '>=1.1',
            'pyopenssl' : '>=19.1.0',
            'pysocks' : '>=1.7.0',
            'python-dateutil' : '>=2.9.0.post0',
            'pyyaml' : '>=5.0.0',
            'send2trash' : '>=1.5.0',
            'service-identity' : '>=18.1.0',
            'show-in-file-manager' : '>=1.1.5',
            'twisted[http2,tls]' : '>=20.3.0',
            'requests' : '==2.32.5',
            'mpv' : '==1.0.8',
            'opencv-python-headless' : '==4.11.0.86',
            'numpy' : '<=2.3.1',
            'pyside6' : '==6.9.3',
            'qtpy' : '==2.4.3',
        }
        
        if sys.platform == 'win32':
            
            requirements_dict.update(
                {
                    'pywin32' : None,
                }
            )
            
        elif sys.platform == 'darwin':
            
            requirements_dict.update(
                {
                    'pyobjc-core' : '>=10.1',
                    'pyobjc-framework-cocoa' : '>=10.1',
                    'pyobjc-framework-quartz' : '>=10.1',
                }
            )
            
        
        # Get installation type
        install_type = get_install_type()
        
        if install_type == "a":
            
            process_advanced_options( requirements_dict )
            
        
        # Create venv
        create_venv( venv_path )
        
        # Install dependencies
        try:
            
            install_dependencies( venv_path, requirements_dict )
            
        except subprocess.CalledProcessError as e:
            
            print( f'ERROR: Installation failed: {e}' )
            
            sys.exit(1)
            
        
        print( '--------' )
        print( 'Done!' )
        
        print()
        
        if sys.platform == 'win32':
            
            python_exe = venv_path / 'Scripts' / 'pythonw.exe'
            
        else:
            
            python_exe = venv_path / 'bin' / 'python'
            
        
        boot_script_path = repo_root / 'hydrus_client.py'
        
        if venv_name == 'venv':
            
            if sys.platform == "win32":
                
                script_name = 'hydrus_client.bat'
                
            elif sys.platform == "darwin":
                
                script_name = 'hydrus_client.command'
                
            else:
                
                script_name = 'hydrus_client.sh'
                
            
            print( f'To start the client, run {script_name} or "{python_exe} {boot_script_path}"' )
            
        else:
            
            print( f'To start the client, run "{python_exe} {boot_script_path}"' )
            
        
    finally:
        
        if sys.platform == 'win32':
            
            # most Win users are double-clicking the file and would appreciate a moment to see the "Done!" conclusion before the window disappears
            input( 'Hit enter to close...' )
            
        
    

if __name__ == "__main__":
    
    main()
    
