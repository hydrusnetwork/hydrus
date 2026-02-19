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

# Default choices for advanced installation
DEFAULT_CHOICES = {
    "qt": "n",
    "mpv": "n",
    "opencv": "n",
    "future": "n",
    "dev": "n",
}


def print_banner():
    """Print the Hydrus ASCII banner."""
    
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
    """Check and display Python version."""
    
    print("--------")
    print("Your Python version is:")
    print(f"Python {sys.version}")
    print()
    
    if sys.version_info < (3, 10):
        
        print("WARNING: Python 3.10+ is required!")
        return False
        
    elif sys.version_info >= ( 3, 14 ):
        
        print( 'You will need the advanced install. Also, select "t" for the (t)est versions of things.' )
        
    
    return True
    

def confirm_venv_delete(venv_path):
    """Check if venv exists and confirm deletion."""
    if venv_path.exists():
        print("Virtual environment will be reinstalled. Press Enter to continue.")
        input()
        print("Deleting old venv...")
        shutil.rmtree(venv_path)
        if venv_path.exists():
            print("ERROR: venv directory did not delete. Is it activated elsewhere, like an IDE?")
            sys.exit(1)
    else:
        print("If you do not know what this is, check the 'running from source' help.")
        print("Press Enter to continue.")
        input()
        
    

def get_install_type():
    """Ask user for simple or advanced install."""
    print()
    print("Do you want the (s)imple or (a)dvanced install?")
    while True:
        install_type = input().strip().lower()
        if install_type in ("s", "a"):
            return install_type
        print("Sorry, did not understand that input! Enter 's' or 'a'.")


def get_user_choice(prompt_text, valid_choices, default_key):
    """
    Get user choice with default fallback.
    
    Args:
        prompt_text: Base prompt text (without default shown)
        valid_choices: Tuple/list of valid choices
        default_key: Key in DEFAULT_CHOICES for default value
    
    Returns:
        The user's choice or default value
    """
    
    while True:
        
        default = DEFAULT_CHOICES[default_key]
        prompt = f"{prompt_text} [{default}]: "
        user_input = input(prompt).strip().lower()
        
        if not user_input:
            
            return default
            
        
        if user_input in valid_choices:
            
            return user_input
            
        
        print("Sorry, did not understand that input!")
        
    

def get_advanced_options():
    """Get advanced configuration options from user."""
    
    print("--------")
    print("We will now choose versions for larger libraries.")
    print("If something doesn't install, run this script again and it will retry.")
    print("Press Enter to use the default choice (shown in brackets).")
    print()
    
    # Qt
    print("Qt - User Interface")
    print("Most people want 'n'.")
    print("Python 3.14 should try 't'.")
    print("If normal Qt doesn't work, try 'o' or 'w'.")
    qt = get_user_choice("Qt choice (o/n/t/q/w)", ("o", "n", "t", "q", "w"), "qt")

    qt_custom_pyside6 = None
    qt_custom_qtpy = None
    if qt == "w":
        print()
        print("Enter the exact PySide6 version, e.g. '6.6.0':")
        print("- Python 3.10: earliest 6.2.0")
        print("- Python 3.11: earliest 6.4.0.1")
        print("- Python 3.12: earliest 6.6.0")
        print("- Python 3.13: earliest 6.8.0.2")
        print("- Python 3.14: earliest 6.10.1")
        qt_custom_pyside6 = input("PySide6 version: ").strip()
        qt_custom_qtpy = input("qtpy version (probably '2.4.3'): ").strip()

    # mpv
    print()
    print("mpv - audio and video playback")
    print("Most people want 'n'.")
    if sys.platform == "darwin":
        print("WARNING: mpv is broken on macOS. Choose 'n' as a safe default.")
    mpv = get_user_choice("mpv choice (n/t)", ("n", "t"), "mpv")

    # OpenCV
    print()
    print("OpenCV - Images")
    print("Most people want 'n'.")
    print("Python 3.11+ should try 't'.")
    opencv = get_user_choice("OpenCV choice (n/t/o)", ("o", "n", "t"), "opencv")

    # Future libraries
    print()
    print("Future Libraries")
    print("There is a test for a new domain parsing library. Want to try it?")
    future = get_user_choice("Future libraries (y/n)", ("y", "n"), "future")

    # Dev mode
    print()
    print("Development Tools")
    print("Do you want to install development tools (PyInstaller, httmock, etc.)?")
    dev = get_user_choice("Install dev tools (y/n)", ("y", "n"), "dev")

    return qt, mpv, opencv, future, dev, qt_custom_pyside6, qt_custom_qtpy
    

def create_venv(venv_path):
    """Create a Python virtual environment."""
    
    print("--------")
    print("Creating new venv...")
    
    subprocess.check_call([sys.executable, "-m", "venv", str(venv_path)])
    

def run_pip(cmd, venv_path):
    """Run pip command in the venv."""
    
    if sys.platform == "win32":
        
        python_exe = venv_path / "Scripts" / "python.exe"
        
    else:
        
        python_exe = venv_path / "bin" / "python"
        
    
    subprocess.check_call([str(python_exe), "-m", "pip"] + cmd)
    

def get_groups_components( groups: list[ str ] ):
    
    # pip install . --group opencv-normal --group qt6-normal --group mpv-normal --group other-normal
    
    groups_components = []
    
    for group in groups:
        
        groups_components.append( '--group' )
        groups_components.append( group )
        
    
    return groups_components
    

def install_dependencies_simple(venv_path):
    """Install simple (base) dependencies with default GUI and media support."""
    
    print("Installing base dependencies with default extras...")
    
    run_pip(["install", "--upgrade", "pip"], venv_path)
    run_pip(["install", "--upgrade", "wheel"], venv_path)
    
    groups = [
        "qt6-normal",           # DEFAULT_CHOICES['qt'] = 'n'
        "mpv-normal",           # DEFAULT_CHOICES['mpv'] = 'n'
        "opencv-normal",        # DEFAULT_CHOICES['opencv'] = 'n'
        "other-normal",      # DEFAULT_CHOICES['future'] = 'n'
    ]
    
    # pip install . --group opencv-normal --group qt6-normal --group mpv-normal --group other-normal
    groups_components = get_groups_components( groups )
    
    print(f"Installing package: {groups}")
    run_pip(['install', '.' ] + groups_components, venv_path)


def install_dependencies_advanced(venv_path, qt, mpv, opencv, future, dev, qt_custom_pyside6, qt_custom_qtpy):
    """Install advanced (customized) dependencies."""
    print("Upgrading pip and wheel...")
    run_pip(["install", "--upgrade", "pip"], venv_path)
    run_pip(["install", "--upgrade", "wheel"], venv_path)

    # Custom Qt versions
    if qt == "w":
        print(f"Installing custom QtPy {qt_custom_qtpy}...")
        try:
            run_pip(["install", f"qtpy=={qt_custom_qtpy}"], venv_path)
        except subprocess.CalledProcessError:
            print(f"ERROR: Could not find qtpy version {qt_custom_qtpy}!")
            sys.exit(1)

        print(f"Installing custom PySide6 {qt_custom_pyside6}...")
        try:
            run_pip(["install", f"PySide6=={qt_custom_pyside6}"], venv_path)
        except subprocess.CalledProcessError:
            print(f"ERROR: Could not find PySide6 version {qt_custom_pyside6}!")
            sys.exit(1)
    
    # Build extras list
    groups = []

    if qt == "n":
        
        groups.append("qt6-normal")
        
    elif qt == "o":
        
        groups.append("qt6-older")
        
    elif qt == "q":
        
        groups.append("qt6-new-pyqt6")
        
    elif qt == "t":
        
        groups.append("qt6-test")
        
    # qt == "w" means custom, already installed above

    if mpv == "n":
        
        groups.append("mpv-normal")
        
    elif mpv == "t":
        
        groups.append("mpv-test")
        

    if opencv == "o":
        
        groups.append("opencv-old")
        
    elif opencv == "n":
        
        groups.append("opencv-normal")
        
    elif opencv == "t":
        
        groups.append("opencv-test")
        

    if future == "y":
        
        groups.append("other-future")
        
    else:
        
        groups.append("other-normal")
        

    if dev == "y":
        
        groups.append("dev")
        
    
    # pip install . --group opencv-normal --group qt6-normal --group mpv-normal --group other-normal
    groups_components = get_groups_components( groups )
    
    # Install with extras
    print(f"Installing package: {groups}")
    run_pip(['install', '.' ] + groups_components, venv_path)
    

def main():
    """Main setup function."""
    
    repo_root = Path(__file__).parent
    os.chdir(repo_root)
    
    argparser = argparse.ArgumentParser( description = 'hydrus network venv setup' )
    
    argparser.add_argument( '-v', '--venv_name', help = 'set the name of the venv folder (default=venv)' )
    
    result = argparser.parse_args()
    
    if result.venv_name is None:
        
        venv_name = 'venv'
        
    else:
        
        venv_name = result.venv_name
        
    
    print_banner()
    
    # Check Python version
    if not check_python_version():
        sys.exit(1)
    
    venv_path = repo_root / venv_name
    
    print( f'venv path: {venv_path}' )
    print()
    
    confirm_venv_delete(venv_path)
    
    # Get installation type
    install_type = get_install_type()
    
    if install_type == "a":
        
        # TODO: write an object to hold this profile for easier editing in future
        qt, mpv, opencv, future, dev, qt_custom_pyside6, qt_custom_qtpy = get_advanced_options()
        
    else:
        
        qt = mpv = opencv = future = dev = None
        qt_custom_pyside6 = qt_custom_qtpy = None
        
    
    # Create venv
    create_venv(venv_path)
    
    # Install dependencies
    try:
        
        if install_type == "s":
            
            install_dependencies_simple(venv_path)
            
        else:
            
            install_dependencies_advanced(venv_path, qt, mpv, opencv, future, dev, qt_custom_pyside6, qt_custom_qtpy)
            
        
    except subprocess.CalledProcessError as e:
        
        print(f"ERROR: Installation failed with exit code {e.returncode}")
        sys.exit(1)
        

    print("--------")
    print("Done!")
    
    print()
    
    if sys.platform == "win32":
        
        python_exe = venv_path / "Scripts" / "pythonw.exe"
        
    else:
        
        python_exe = venv_path / "bin" / "python"
        
    
    boot_script_path = repo_root / 'hydrus_client.py'
    
    if venv_name == 'venv':
        
        if sys.platform == "win32":
            
            print( f'To start the client, run hydrus_client.bat or "{python_exe} {boot_script_path}"' )
            
            input()
            
        elif sys.platform == "darwin":
            
            print( f'To start the client, run hydrus_client.command or "{python_exe} {boot_script_path}"' )
            
        else:
            
            print( f'To start the client, run hydrus_client.sh or "{python_exe} {boot_script_path}"' )
            
        
    

if __name__ == "__main__":
    
    main()
    
